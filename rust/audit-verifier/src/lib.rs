use serde::de::{Error as DeError, SeqAccess, Visitor};
use serde::Deserializer;
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use std::fmt;
use std::io::Read;

pub const GENESIS_HASH: &str = "0000000000000000000000000000000000000000000000000000000000000000";
const MAX_SAFE_INTEGER: u64 = 9_007_199_254_740_991;

#[derive(Debug, PartialEq, Eq)]
pub struct Verification {
    pub event_count: usize,
    pub head_hash: String,
}

#[derive(Debug, PartialEq, Eq)]
pub enum VerifyError {
    RootMustBeArray,
    EventMustBeObject { index: usize },
    MissingPreviousHash { index: usize },
    InvalidPreviousHash { index: usize },
    MissingEventHash { index: usize },
    InvalidEventHash { index: usize },
    Canonicalization { index: usize },
    InvalidJson { message: String },
    ExpectedHeadMismatch { expected: String, actual: String },
}

impl fmt::Display for VerifyError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::RootMustBeArray => write!(formatter, "audit log root must be a JSON array"),
            Self::EventMustBeObject { index } => {
                write!(formatter, "event {index} is not a JSON object")
            }
            Self::MissingPreviousHash { index } => {
                write!(formatter, "event {index} is missing previous_hash")
            }
            Self::InvalidPreviousHash { index } => {
                write!(formatter, "event {index} has an invalid previous_hash")
            }
            Self::MissingEventHash { index } => {
                write!(formatter, "event {index} is missing event_hash")
            }
            Self::InvalidEventHash { index } => {
                write!(formatter, "event {index} has an invalid event_hash")
            }
            Self::Canonicalization { index } => {
                write!(formatter, "event {index} could not be canonicalized")
            }
            Self::InvalidJson { message } => write!(formatter, "invalid audit JSON: {message}"),
            Self::ExpectedHeadMismatch { expected, actual } => write!(
                formatter,
                "audit log head does not match trusted checkpoint (expected {expected}, got {actual})"
            ),
        }
    }
}

impl std::error::Error for VerifyError {}

pub fn hash_event(event: &Value) -> Result<String, String> {
    let mut unsigned = event
        .as_object()
        .cloned()
        .ok_or_else(|| "event must be a JSON object".to_string())?;
    if contains_unsupported_number(event) {
        return Err("event contains a floating-point or unsafe integer value".to_string());
    }
    unsigned.remove("event_hash");
    let canonical =
        serde_json::to_vec(&Value::Object(unsigned)).map_err(|error| error.to_string())?;
    let digest = Sha256::digest(canonical);
    Ok(digest.iter().map(|byte| format!("{byte:02x}")).collect())
}

fn contains_unsupported_number(value: &Value) -> bool {
    match value {
        Value::Number(number) => match (number.as_i64(), number.as_u64()) {
            (Some(signed), _) => signed.unsigned_abs() > MAX_SAFE_INTEGER,
            (_, Some(unsigned)) => unsigned > MAX_SAFE_INTEGER,
            _ => true,
        },
        Value::Array(values) => values.iter().any(contains_unsupported_number),
        Value::Object(fields) => fields.values().any(contains_unsupported_number),
        _ => false,
    }
}

struct VerifyState {
    event_count: usize,
    head_hash: String,
    failure: Option<VerifyError>,
}

impl VerifyState {
    fn new() -> Self {
        Self {
            event_count: 0,
            head_hash: GENESIS_HASH.to_string(),
            failure: None,
        }
    }

    fn verify_event(&mut self, event: Value) -> Result<(), VerifyError> {
        let index = self.event_count;
        let object = event
            .as_object()
            .ok_or(VerifyError::EventMustBeObject { index })?;
        let recorded_previous = object
            .get("previous_hash")
            .and_then(Value::as_str)
            .ok_or(VerifyError::MissingPreviousHash { index })?;
        if recorded_previous != self.head_hash {
            return Err(VerifyError::InvalidPreviousHash { index });
        }

        let recorded_event_hash = object
            .get("event_hash")
            .and_then(Value::as_str)
            .ok_or(VerifyError::MissingEventHash { index })?;
        let calculated = hash_event(&event).map_err(|_| VerifyError::Canonicalization { index })?;
        if recorded_event_hash != calculated {
            return Err(VerifyError::InvalidEventHash { index });
        }

        self.head_hash = calculated;
        self.event_count += 1;
        Ok(())
    }
}

struct VerifyVisitor<'a> {
    state: &'a mut VerifyState,
}

impl<'de> Visitor<'de> for VerifyVisitor<'_> {
    type Value = ();

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("an array of audit event objects")
    }

    fn visit_seq<A>(self, mut sequence: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        while let Some(event) = sequence.next_element::<Value>()? {
            if let Err(error) = self.state.verify_event(event) {
                let message = error.to_string();
                self.state.failure = Some(error);
                return Err(A::Error::custom(message));
            }
        }
        Ok(())
    }

    fn visit_map<A>(self, _map: A) -> Result<Self::Value, A::Error>
    where
        A: serde::de::MapAccess<'de>,
    {
        self.state.failure = Some(VerifyError::RootMustBeArray);
        Err(A::Error::custom("audit log root must be a JSON array"))
    }
}

pub fn verify_reader<R: Read>(
    reader: R,
    expected_head: Option<&str>,
) -> Result<Verification, VerifyError> {
    let mut state = VerifyState::new();
    let mut deserializer = serde_json::Deserializer::from_reader(reader);
    let parse_result = deserializer.deserialize_any(VerifyVisitor { state: &mut state });
    if let Some(error) = state.failure {
        return Err(error);
    }
    parse_result.map_err(|error| VerifyError::InvalidJson {
        message: error.to_string(),
    })?;
    deserializer
        .end()
        .map_err(|error| VerifyError::InvalidJson {
            message: error.to_string(),
        })?;

    if let Some(expected) = expected_head {
        if state.head_hash != expected {
            return Err(VerifyError::ExpectedHeadMismatch {
                expected: expected.to_string(),
                actual: state.head_hash,
            });
        }
    }

    Ok(Verification {
        event_count: state.event_count,
        head_hash: state.head_hash,
    })
}

pub fn verify_document(
    document: &Value,
    expected_head: Option<&str>,
) -> Result<Verification, VerifyError> {
    verify_reader(document.to_string().as_bytes(), expected_head)
}

pub fn make_event(fields: &[(&str, Value)], previous_hash: &str) -> Value {
    let mut object = Map::new();
    for (key, value) in fields {
        object.insert((*key).to_string(), value.clone());
    }
    object.insert(
        "previous_hash".to_string(),
        Value::String(previous_hash.to_string()),
    );
    let mut event = Value::Object(object);
    let hash = hash_event(&event).expect("a JSON object can be serialized");
    event
        .as_object_mut()
        .expect("event is an object")
        .insert("event_hash".to_string(), Value::String(hash));
    event
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    const VALID_FIXTURE: &str = include_str!("../../../tests/fixtures/audit_chain_valid.json");
    const TAMPERED_FIXTURE: &str =
        include_str!("../../../tests/fixtures/audit_chain_tampered.json");
    const FIXTURE_HEAD: &str = "ef64c56db877472454c6f6297b636e0a55bd1bcf02667017bf86c435a4008fde";

    fn valid_chain() -> Value {
        let first = make_event(
            &[
                ("operation", json!("balance_lookup")),
                ("timestamp", json!("2026-01-01T00:00:00+00:00")),
            ],
            GENESIS_HASH,
        );
        let previous = first["event_hash"].as_str().expect("first hash");
        let second = make_event(&[("operation", json!("transfer"))], previous);
        json!([first, second])
    }

    #[test]
    fn accepts_empty_and_linked_logs() {
        assert_eq!(
            verify_document(&json!([]), None)
                .expect("empty chain is valid")
                .event_count,
            0
        );
        assert_eq!(
            verify_document(&valid_chain(), None)
                .expect("linked chain is valid")
                .event_count,
            2
        );
    }

    #[test]
    fn python_shared_fixture_matches_rust_hashing_and_checkpoint() {
        let verification = verify_reader(VALID_FIXTURE.as_bytes(), Some(FIXTURE_HEAD))
            .expect("Python-generated fixture should verify in Rust");
        assert_eq!(verification.event_count, 2);
        assert_eq!(verification.head_hash, FIXTURE_HEAD);
    }

    #[test]
    fn both_languages_reject_the_shared_tampered_fixture() {
        assert_eq!(
            verify_reader(TAMPERED_FIXTURE.as_bytes(), None),
            Err(VerifyError::InvalidEventHash { index: 0 })
        );
    }

    #[test]
    fn trusted_checkpoint_detects_truncated_tail() {
        let first_event = valid_chain()[0].clone();
        let truncated = json!([first_event]).to_string();
        assert!(matches!(
            verify_reader(truncated.as_bytes(), Some(FIXTURE_HEAD)),
            Err(VerifyError::ExpectedHeadMismatch { .. })
        ));
    }

    #[test]
    fn rejects_modified_event_content() {
        let mut document = valid_chain();
        document[0]["operation"] = json!("tampered");
        assert_eq!(
            verify_document(&document, None),
            Err(VerifyError::InvalidEventHash { index: 0 })
        );
    }

    #[test]
    fn rejects_reordered_events() {
        let chain = valid_chain();
        let reordered = json!([chain[1].clone(), chain[0].clone()]);
        assert_eq!(
            verify_document(&reordered, None),
            Err(VerifyError::InvalidPreviousHash { index: 0 })
        );
    }

    #[test]
    fn rejects_unhashed_legacy_events_and_non_array_roots() {
        assert_eq!(
            verify_document(&json!([{"operation":"legacy"}]), None),
            Err(VerifyError::MissingPreviousHash { index: 0 })
        );
        assert_eq!(
            verify_document(&json!({"events": []}), None),
            Err(VerifyError::RootMustBeArray)
        );
    }

    #[test]
    fn rejects_trailing_and_malformed_json() {
        assert!(matches!(
            verify_reader(b"[] trailing".as_slice(), None),
            Err(VerifyError::InvalidJson { .. })
        ));
        assert!(verify_reader(b"[{}".as_slice(), None).is_err());
    }

    #[test]
    fn rejects_floating_point_and_unsafe_integers() {
        assert!(hash_event(&json!({"amount": 1.25})).is_err());
        assert!(hash_event(&json!({"amount": 9007199254740992_u64})).is_err());
    }
}
