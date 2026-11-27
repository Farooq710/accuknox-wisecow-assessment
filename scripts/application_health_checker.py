#!/usr/bin/env python3

import argparse
import logging
import math
import ssl
import time

from pathlib import Path
from logging.handlers import RotatingFileHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit


def positive_number(value):
    value = float(value)

    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(
            "Value must be greater than zero"
        )

    return value


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="HTTP/HTTPS Application Health Checker"
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Application URL to monitor"
    )

    parser.add_argument(
        "--interval",
        type=positive_number,
        default=10
    )

    parser.add_argument(
        "--timeout",
        type=positive_number,
        default=5
    )

    parser.add_argument(
        "--response-threshold",
        type=positive_number,
        default=1000,
        help="Response time warning threshold in milliseconds"
    )

    parser.add_argument(
        "--ca-cert",
        help="Path to a trusted custom TLS certificate"
    )

    parser.add_argument(
        "--log-file",
        default="logs/application_health.log"
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Perform a single application health check"
    )

    args = parser.parse_args()
    parsed_url = urlsplit(args.url)

    if parsed_url.scheme not in ("http", "https"):
        parser.error("URL must use HTTP or HTTPS")

    if not parsed_url.hostname:
        parser.error("A valid hostname is required")

    return args


def setup_logger(log_file):
    Path(log_file).parent.mkdir(
        parents=True, exist_ok=True
    )

    logger = logging.getLogger("application_health")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )

    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def check_application(args, logger, ssl_context):
    start_time = time.monotonic()

    try:
        request = Request(
            args.url,
            headers={
                "User-Agent": "ApplicationHealthChecker/1.0"
            },
            method="GET"
        )

        with urlopen(
            request,
            timeout=args.timeout,
            context=ssl_context
        ) as response:

            status_code = response.status
            response.read(4096)

            response_time = (
                time.monotonic() - start_time
            ) * 1000

            if 200 <= status_code < 300:
                logger.info(
                    "STATUS: UP | HTTP: %d | "
                    "Response Time: %.2f ms | URL: %s",
                    status_code,
                    response_time,
                    args.url
                )

                if response_time > args.response_threshold:
                    logger.warning(
                        "Slow response detected: %.2f ms "
                        "> %.2f ms",
                        response_time,
                        args.response_threshold
                    )

                return True

            logger.error(
                "STATUS: DOWN | HTTP: %d | URL: %s",
                status_code,
                args.url
            )

            return False

    except HTTPError as error:
        logger.error(
            "STATUS: DOWN | HTTP: %d | Reason: %s",
            error.code,
            error.reason
        )
        error.close()

    except URLError as error:
        logger.error(
            "STATUS: DOWN | Connection Error: %s",
            error.reason
        )

    except TimeoutError:
        logger.error(
            "STATUS: DOWN | Request timed out"
        )

    except (OSError, ValueError) as error:
        logger.error(
            "STATUS: DOWN | Error: %s",
            error
        )

    return False


def main():
    args = parse_arguments()
    logger = setup_logger(args.log_file)

    try:
        ssl_context = ssl.create_default_context(
            cafile=args.ca_cert
        )

    except (OSError, ssl.SSLError) as error:
        logger.error("TLS configuration failed: %s", error)
        return 1

    logger.info("Application Health Checker started")
    logger.info("Monitoring URL: %s", args.url)
    logger.info("Monitoring interval: %s seconds", args.interval)
    logger.info("Request timeout: %s seconds", args.timeout)
    logger.info("TLS certificate verification: Enabled for HTTPS")

    try:
        while True:
            healthy = check_application(
                args, logger, ssl_context
            )

            if args.once:
                return 0 if healthy else 1

            time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")

    finally:
        logger.info("Application Health Checker terminated")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
