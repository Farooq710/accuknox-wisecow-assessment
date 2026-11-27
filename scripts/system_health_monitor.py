#!/usr/bin/env python3

import argparse
import logging
import time
import socket
from logging.handlers import RotatingFileHandler
from pathlib import Path

import psutil


def percentage(value):
    value = float(value)
    if not 0 <= value <= 100:
        raise argparse.ArgumentTypeError(
            "Threshold must be between 0 and 100"
        )
    return value


def positive_integer(value):
    value = int(value)
    if value <= 0:
        raise argparse.ArgumentTypeError(
            "Value must be greater than zero"
        )
    return value


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Linux System Health Monitoring Tool"
    )

    parser.add_argument("--cpu", type=percentage, default=80)
    parser.add_argument("--memory", type=percentage, default=80)
    parser.add_argument("--disk", type=percentage, default=80)
    parser.add_argument(
        "--processes", type=positive_integer, default=300
    )
    parser.add_argument(
        "--interval", type=positive_integer, default=10
    )
    parser.add_argument("--disk-path", default="/")
    parser.add_argument(
        "--log-file", default="logs/system_health.log"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Perform a single health check"
    )

    return parser.parse_args()


def setup_logger(log_file):
    Path(log_file).parent.mkdir(
        parents=True, exist_ok=True
    )

    logger = logging.getLogger("system_health")
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


def collect_metrics(disk_path):
    return {
        "cpu": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage(disk_path).percent,
        "processes": len(psutil.pids())
    }


def get_top_processes(limit=5):
    processes = []

    for process in psutil.process_iter(
        ["pid", "name", "memory_percent"]
    ):
        try:
            info = process.info

            if info["memory_percent"] is not None:
                processes.append(info)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return sorted(
        processes,
        key=lambda process: process["memory_percent"],
        reverse=True
    )[:limit]


def evaluate_metrics(metrics, thresholds, logger):
    alerts = []

    for metric, value in metrics.items():
        threshold = thresholds[metric]
        unit = "" if metric == "processes" else "%"

        if value > threshold:
            message = (
                f"{metric.upper()} threshold exceeded: "
                f"{value}{unit} > {threshold}{unit}"
            )

            logger.warning(message)
            alerts.append(message)

    return alerts


def monitor_system(args, logger):
    metrics = collect_metrics(args.disk_path)

    logger.info(
        "CPU: %.1f%% | Memory: %.1f%% | "
        "Disk: %.1f%% | Processes: %d",
        metrics["cpu"],
        metrics["memory"],
        metrics["disk"],
        metrics["processes"]
    )

    thresholds = {
        "cpu": args.cpu,
        "memory": args.memory,
        "disk": args.disk,
        "processes": args.processes
    }

    alerts = evaluate_metrics(
        metrics, thresholds, logger
    )

    if alerts:
        logger.warning(
            "SYSTEM STATUS: WARNING | %d threshold(s) exceeded",
            len(alerts)
        )

        if metrics["memory"] > args.memory:
            logger.info("Top 5 memory-consuming processes:")

            for process in get_top_processes():
                logger.info(
                    "PID: %s | Process: %s | Memory: %.2f%%",
                    process["pid"],
                    process["name"],
                    process["memory_percent"]
                )
    else:
        logger.info("SYSTEM STATUS: HEALTHY")


def main():
    args = parse_arguments()
    logger = setup_logger(args.log_file)

    logger.info("System Health Monitor started")
    logger.info("Hostname: %s", socket.gethostname())

    logger.info(
        "Thresholds | CPU: %s%% | Memory: %s%% | "
        "Disk: %s%% | Processes: %s",
        args.cpu,
        args.memory,
        args.disk,
        args.processes
    )

    try:
        while True:
            try:
                monitor_system(args, logger)

            except (OSError, psutil.Error) as error:
                logger.error(
                    "Metric collection failed: %s", error
                )

                if args.once:
                    return 1

            if args.once:
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")

    finally:
        logger.info("System Health Monitor terminated")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
