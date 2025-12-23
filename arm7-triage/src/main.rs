use std::env;

fn double(n: i32) -> i32 {
    n * 2
}

fn format_result(n: i32) -> String {
    format!("Result: {}", double(n))
}

fn parse_arg(arg: &str) -> Result<i32, String> {
    arg.parse::<i32>()
        .map_err(|_| format!("Error: '{}' is not a valid integer", arg))
}

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() != 2 {
        eprintln!("Usage: {} <number>", args[0]);
        std::process::exit(1);
    }

    let input: i32 = match parse_arg(&args[1]) {
        Ok(n) => n,
        Err(msg) => {
            eprintln!("{}", msg);
            std::process::exit(1);
        }
    };

    println!("{}", format_result(input));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn double_works_for_positive_numbers() {
        assert_eq!(double(5), 10);
        assert_eq!(double(7), 14);
    }

    #[test]
    fn double_works_for_zero() {
        assert_eq!(double(0), 0);
    }

    #[test]
    fn double_works_for_negative_numbers() {
        assert_eq!(double(-3), -6);
    }

    #[test]
    fn format_result_matches_cli_output_format() {
        assert_eq!(format_result(5), "Result: 10");
        assert_eq!(format_result(7), "Result: 14");
    }

    #[test]
    fn parse_arg_accepts_valid_integer() {
        assert_eq!(parse_arg("42").unwrap(), 42);
    }

    #[test]
    fn parse_arg_rejects_invalid_integer_with_expected_message() {
        assert_eq!(
            parse_arg("abc").unwrap_err(),
            "Error: 'abc' is not a valid integer"
        );
    }
}
