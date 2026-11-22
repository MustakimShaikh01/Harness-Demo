use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use std::fmt;

pub const GENESIS_HASH: &str = "0000000000000000000000000000000000000000000000000000000000000000";

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
        }
    }
}

impl std::error::Error for VerifyError {}

pub fn hash_event(event: &Value) -> Result<String, String> {
    let mut unsigned = event
        .as_object()
        .cloned()
        .ok_or_else(|| "event must be a JSON object".to_string())?;
    unsigned.remove("event_hash");
    let canonical =
        serde_json::to_vec(&Value::Object(unsigned)).map_err(|error| error.to_string())?;
    let digest = Sha256::digest(canonical);
    Ok(digest.iter().map(|byte| format!("{byte:02x}")).collect())
}

pub fn verify_document(document: &Value) -> Result<Verification, VerifyError> {
    let events = document.as_array().ok_or(VerifyError::RootMustBeArray)?;
    let mut expected_previous = GENESIS_HASH.to_string();

    for (index, event) in events.iter().enumerate() {
        let object = event
            .as_object()
            .ok_or(VerifyError::EventMustBeObject { index })?;
        let recorded_previous = object
            .get("previous_hash")
            .and_then(Value::as_str)
            .ok_or(VerifyError::MissingPreviousHash { index })?;
        if recorded_previous != expected_previous {
            return Err(VerifyError::InvalidPreviousHash { index });
        }

        let recorded_event_hash = object
            .get("event_hash")
            .and_then(Value::as_str)
            .ok_or(VerifyError::MissingEventHash { index })?;
        let calculated = hash_event(event).map_err(|_| VerifyError::Canonicalization { index })?;
        if recorded_event_hash != calculated {
            return Err(VerifyError::InvalidEventHash { index });
        }
        expected_previous = calculated;
    }

    Ok(Verification {
        event_count: events.len(),
        head_hash: expected_previous,
    })
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
    fn accepts_valid_empty_and_linked_logs() {
        assert_eq!(
            verify_document(&json!([]))
                .expect("empty chain is valid")
                .event_count,
            0
        );
        assert_eq!(
            verify_document(&valid_chain())
                .expect("linked chain is valid")
                .event_count,
            2
        );
    }

    #[test]
    fn rejects_modified_event_content() {
        let mut document = valid_chain();
        document[0]["operation"] = json!("tampered");
        assert_eq!(
            verify_document(&document),
            Err(VerifyError::InvalidEventHash { index: 0 })
        );
    }

    #[test]
    fn rejects_reordered_or_removed_events() {
        let chain = valid_chain();
        let reordered = json!([chain[1].clone(), chain[0].clone()]);
        assert_eq!(
            verify_document(&reordered),
            Err(VerifyError::InvalidPreviousHash { index: 0 })
        );
    }

    #[test]
    fn rejects_unhashed_legacy_events() {
        assert_eq!(
            verify_document(&json!([{"operation":"legacy"}])),
            Err(VerifyError::MissingPreviousHash { index: 0 })
        );
    }
}
