use bankguard_audit_verifier::verify_reader;
use std::env;
use std::fs::File;
use std::io::BufReader;
use std::process::ExitCode;

fn usage() {
    eprintln!(
        "Usage: bankguard-audit-verifier verify <audit_logs.json> [--expected-head <sha256>]"
    );
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().skip(1).collect();
    let Some(command) = args.first() else {
        usage();
        return Err("missing command".to_string());
    };
    let Some(path) = args.get(1) else {
        usage();
        return Err("missing audit log path".to_string());
    };
    let expected_head = match args.as_slice() {
        [_, _, flag, hash] if flag == "--expected-head" => {
            if hash.len() != 64 || !hash.bytes().all(|byte| byte.is_ascii_hexdigit()) {
                return Err(
                    "expected head must be a 64-character hexadecimal SHA-256 hash".to_string(),
                );
            }
            Some(hash.as_str())
        }
        [_, _] => None,
        _ => {
            usage();
            return Err("invalid arguments".to_string());
        }
    };
    if command != "verify" {
        usage();
        return Err(format!("unknown command: {command}"));
    }

    let file = File::open(path).map_err(|error| format!("cannot open {path}: {error}"))?;
    let verification =
        verify_reader(BufReader::new(file), expected_head).map_err(|error| error.to_string())?;
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
