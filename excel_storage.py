"""Merge crawler records into Excel files without discarding previous runs."""

import os
import tempfile
from pathlib import Path

import pandas as pd


class ExcelPersistenceError(RuntimeError):
    """Raised when an Excel workbook could not be preserved or updated."""


def _merge_records(existing: list[pd.DataFrame], records: list[dict]) -> pd.DataFrame:
    frames = [frame for frame in existing if not frame.empty]
    if records:
        frames.append(pd.DataFrame(records))
    if not frames:
        return pd.DataFrame()

    merged = pd.concat(frames, ignore_index=True, sort=False)
    url_column = next((column for column in ('Ghi chú', 'url') if column in merged.columns), None)
    if url_column is None:
        url_column = next(
            (
                column for column in merged.columns
                if str(column).strip().lower().startswith('ghi ch')
            ),
            None,
        )
    if url_column is None:
        return merged

    url_keys = merged[url_column].fillna('').astype(str).str.strip()
    has_url = url_keys.ne('')
    with_url = merged.loc[has_url].copy()
    with_url['_excel_url_key'] = url_keys.loc[has_url]
    with_url['_excel_order'] = merged.index[has_url]
    with_url = with_url.replace('', pd.NA)
    with_url = (
        with_url.groupby('_excel_url_key', sort=False)
        .last()
        .sort_values('_excel_order')
        .drop(columns='_excel_order')
        .reset_index(drop=True)
    )
    without_url = merged.loc[~has_url]
    return pd.concat([with_url, without_url], ignore_index=True)


def _write_atomically(frame: pd.DataFrame, destination: Path) -> None:
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f'.{destination.stem}_',
            suffix=destination.suffix,
            dir=destination.parent,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
        frame.to_excel(temp_path, index=False)
        os.replace(temp_path, destination)
    except BaseException:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def save_records_to_excel(records: list[dict], file_path: str) -> Path | None:
    """Preserve existing rows and update jobs with matching URLs."""
    destination = Path(file_path)
    fallback = destination.with_name(f'{destination.stem}_out{destination.suffix}')
    try:
        existing = [
            pd.read_excel(path)
            for path in (fallback, destination)
            if path.exists()
        ]
        frame = _merge_records(existing, records)
        if frame.empty:
            return None

        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            _write_atomically(frame, destination)
            return destination
        except PermissionError:
            _write_atomically(frame, fallback)
            return fallback
    except Exception as exc:
        raise ExcelPersistenceError(
            f"Khong the bao toan/cap nhat file Excel '{destination}'. "
            "Hay dong workbook dang mo va kiem tra quyen ghi."
        ) from exc
