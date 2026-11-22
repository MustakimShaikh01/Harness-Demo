use bankguard_audit_verifier::verify_document;
use serde_json::Value;
use std::env;
use std::fs;
use std::process::ExitCode;

fn usage() {
    eprintln!("Usage: bankguard-audit-verifier verify <audit_logs.json>");
}

fn run() -> Result<(), String> {
    let mut args = env::args().skip(1);
    let Some(command) = args.next() else {
        usage();
        return Err("missing command".to_string());
    };
    let Some(path) = args.next() else {
        usage();
        return Err("missing audit log path".to_string());
    };
    if command != "verify" || args.next().is_some() {
        usage();
        return Err("invalid arguments".to_string());
    }

    let contents =
        fs::read_to_string(&path).map_err(|error| format!("cannot read {path}: {error}"))?;
    let document: Value = serde_json::from_str(&contents)
        .map_err(|error| format!("invalid JSON in {path}: {error}"))?;
    let verification = verify_document(&document).map_err(|error| error.to_string())?;
    println!(
        "OK: verified {} audit events; head_hash={}",
        verification.event_count, verification.head_hash
    );
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("Audit verification failed: {error}");
            ExitCode::FAILURE
        }
    }
}
