from __future__ import annotations

import argparse
import os
import sys

import audittrail
from audittrail import RiskLevel
from audittrail.exporters.json_exporter import export_compliance_report
from audittrail.utils.integrity import verify_chain


def _parse_risk_level(value: str) -> RiskLevel:
    try:
        return RiskLevel[value.upper()]
    except KeyError as exc:
        raise argparse.ArgumentTypeError(
            "risk_level must be one of: MINIMAL, LIMITED, HIGH, UNACCEPTABLE"
        ) from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audittrail-cli",
        description="AuditTrail CLI for exporting compliance reports and verifying audit logs.",
    )
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument(
        "--risk-level",
        required=True,
        type=_parse_risk_level,
        help="Risk level (MINIMAL, LIMITED, HIGH, UNACCEPTABLE)",
    )
    parser.add_argument(
        "--output-dir", default="./audit_logs", help="Audit output directory"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    export_cmd = sub.add_parser("export-report", help="Export compliance report")
    export_cmd.add_argument(
        "--trace-ids",
        nargs="*",
        default=None,
        help="Optional list of trace IDs to include",
    )
    export_cmd.add_argument(
        "--output-path",
        default=None,
        help="Optional output path for report JSON",
    )
    export_cmd.add_argument(
        "--output-dir",
        default=None,
        help="Optional audit output directory (overrides global)",
    )

    verify_cmd = sub.add_parser("verify-chain", help="Verify audit log hash chain")
    verify_cmd.add_argument(
        "--log-path",
        default=None,
        help="Optional log path (defaults to project log)",
    )
    verify_cmd.add_argument(
        "--output-dir",
        default=None,
        help="Optional audit output directory (overrides global)",
    )

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    cmd_output_dir = getattr(args, "output_dir", None) or args.output_dir
    audittrail.init(
        project=args.project, risk_level=args.risk_level, output_dir=cmd_output_dir
    )

    if args.command == "export-report":
        path = export_compliance_report(
            trace_ids=args.trace_ids, output_path=args.output_path
        )
        print(path)
        return 0

    if args.command == "verify-chain":
        if args.log_path:
            log_path = args.log_path
        else:
            candidate = f"{cmd_output_dir}/{args.project}_audit.log"
            if os.path.exists(candidate):
                log_path = candidate
            else:
                demo_candidate = f"./demo_output/{args.project}_audit.log"
                if os.path.exists(demo_candidate):
                    log_path = demo_candidate
                else:
                    print(
                        "log file not found; use --log-path or --output-dir",
                        file=sys.stderr,
                    )
                    return 1
        valid = verify_chain(log_path)
        print("valid" if valid else "invalid")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
