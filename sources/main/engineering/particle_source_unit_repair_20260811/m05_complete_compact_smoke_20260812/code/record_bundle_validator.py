#!/usr/bin/env python3
"""Compatibility entry point for the single m05cc-v2 validator authority.

The executable implementation lives only in :mod:`record_validation`; keeping
two copies previously allowed scalar and empty-diagnostics rules to drift.
"""

from record_validation import (  # noqa: F401
    SCHEMA_PATH,
    WHITELIST_PATH,
    ValidationError,
    main,
    validate_bundle,
)

RecordContractError = ValidationError

if __name__ == "__main__":
    raise SystemExit(main())
