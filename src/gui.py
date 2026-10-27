"""데스크톱 GUI (tkinter).

터미널 없이 엑셀 파일을 골라 실행하고 결과 엑셀을 생성하는 창을 띄운다.
핵심 분석 로직은 src.main.run() 을 그대로 호출하며, 이 파일은 오직 화면/입력만 담당한다.

실행:
    python -m src.gui

Windows 에서 Python 설치 시 tkinter 는 기본 포함되어 있다.
"""
from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.main import run

APP_TITLE = "소모품 교체 준수 판정기"
DEFAULT_CONFIG_DIR = Path("config")
DEFAULT_OUT_DIR = Path("output")


def _open_folder(path: Path) -> None:
    """결과가 저장된 폴더를 OS 탐색기로 연다(가능한 경우)."""
    try:
        path = path.resolve()
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.resizable(False, False)

        self.prod_path: Path | None = None
        self.master_path: Path | None = None
        self.smes_paths: list[Path] = []

        self._build_ui()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self, padding=16)
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(
            frm,
            text="엑셀 3종을 선택하고 기준일을 입력한 뒤 [실행]을 누르세요.",
            font=("", 10, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(frm, text="① 생산팀 교체이력 (.xlsx)").grid(
            row=1, column=0, sticky="w", padx=10, pady=6
        )
        self.prod_label = ttk.Label(frm, text="(선택 안 됨)", foreground="#888", width=42)
        self.prod_label.grid(row=1, column=1, sticky="w", padx=10, pady=6)
        ttk.Button(frm, text="파일 선택", command=self._pick_prod).grid(
            row=1, column=2, padx=10, pady=6
        )

        ttk.Label(frm, text="③ 교체주기 마스터 (.xlsx)").grid(
            row=2, column=0, sticky="w", padx=10, pady=6
        )
        self.master_label = ttk.Label(frm, text="(선택 안 됨)", foreground="#888", width=42)
        self.master_label.grid(row=2, column=1, sticky="w", padx=10, pady=6)
        ttk.Button(frm, text="파일 선택", command=self._pick_master).grid(
            row=2, column=2, padx=10, pady=6
        )

        ttk.Label(frm, text="② SMES 교체이력 (.xls, 복수)").grid(
            row=3, column=0, sticky="w", padx=10, pady=6
        )
        self.smes_label = ttk.Label(frm, text="(선택 안 됨)", foreground="#888", width=42)
        self.smes_label.grid(row=3, column=1, sticky="w", padx=10, pady=6)
        ttk.Button(frm, text="파일 선택", command=self._pick_smes).grid(
            row=3, column=2, padx=10, pady=6
        )

        ttk.Label(frm, text="기준일 (YYYY-MM-DD)").grid(
            row=4, column=0, sticky="w", padx=10, pady=6
        )
        self.date_var = tk.StringVar(value=dt.date.today().isoformat())
        ttk.Entry(frm, textvariable=self.date_var, width=18).grid(
            row=4, column=1, sticky="w", padx=10, pady=6
        )

        self.run_btn = ttk.Button(frm, text="실행", command=self._on_run)
        self.run_btn.grid(row=5, column=0, columnspan=3, sticky="ew", padx=10, pady=(14, 6))

        self.status_var = tk.StringVar(value="대기 중")
        self.status_label = ttk.Label(frm, textvariable=self.status_var, foreground="#555")
        self.status_label.grid(row=6, column=0, columnspan=3, sticky="w", padx=10, pady=6)

    def _pick_prod(self) -> None:
        path = filedialog.askopenfilename(
            title="생산팀 교체이력 (.xlsx) 선택",
            filetypes=[("Excel 통합문서", "*.xlsx"), ("모든 파일", "*.*")],
        )
        if path:
            self.prod_path = Path(path)
            self.prod_label.config(text=self.prod_path.name, foreground="#000")

    def _pick_master(self) -> None:
        path = filedialog.askopenfilename(
            title="교체주기 마스터 (.xlsx) 선택",
            filetypes=[("Excel 통합문서", "*.xlsx"), ("모든 파일", "*.*")],
        )
        if path:
            self.master_path = Path(path)
            self.master_label.config(text=self.master_path.name, foreground="#000")

    def _pick_smes(self) -> None:
        paths = filedialog.askopenfilenames(
            title="SMES 교체이력 (.xls) 선택 — 여러 개 가능",
            filetypes=[("구 Excel 97-2003", "*.xls"), ("모든 파일", "*.*")],
        )
        if paths:
            self.smes_paths = [Path(p) for p in paths]
            if len(self.smes_paths) == 1:
                text = self.smes_paths[0].name
            else:
                text = f"{len(self.smes_paths)}개 파일 선택됨"
            self.smes_label.config(text=text, foreground="#000")

    def _validate(self) -> tuple[dt.date, Path, list[Path], Path] | None:
        if self.prod_path is None:
            messagebox.showwarning(APP_TITLE, "① 생산팀 교체이력 파일을 선택하세요.")
            return None
        if self.master_path is None:
            messagebox.showwarning(APP_TITLE, "③ 교체주기 마스터 파일을 선택하세요.")
            return None
        if not self.smes_paths:
            messagebox.showwarning(APP_TITLE, "② SMES 교체이력 파일을 선택하세요.")
            return None
        try:
            as_of = dt.date.fromisoformat(self.date_var.get().strip())
        except ValueError:
            messagebox.showwarning(
                APP_TITLE, "기준일 형식이 올바르지 않습니다. 예: 2026-10-22"
            )
            return None
        return as_of, self.prod_path, self.smes_paths, self.master_path

    def _on_run(self) -> None:
        validated = self._validate()
        if validated is None:
            return
        as_of, prod_path, smes_paths, master_path = validated

        self.run_btn.config(state="disabled")
        self.status_var.set("실행 중… 잠시만 기다려 주세요.")
        self.status_label.config(foreground="#555")

        # 분석은 별도 스레드에서 돌려 창이 멈추지 않게 한다.
        thread = threading.Thread(
            target=self._run_worker,
            args=(as_of, prod_path, smes_paths, master_path),
            daemon=True,
        )
        thread.start()

    def _run_worker(
        self, as_of: dt.date, prod_path: Path, smes_paths: list[Path], master_path: Path
    ) -> None:
        try:
            # smes 인자는 단일 파일이면 Path, 복수면 list[Path] 로 넘긴다(run 시그니처 호환).
            smes_arg = smes_paths[0] if len(smes_paths) == 1 else smes_paths
            DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
            out_path = run(
                as_of,
                prod_path,
                smes_arg,
                master_path,
                DEFAULT_CONFIG_DIR,
                DEFAULT_OUT_DIR,
            )
        except Exception as exc:  # noqa: BLE001 - 사용자에게 원인을 그대로 보여준다
            detail = traceback.format_exc()
            self.after(0, self._on_error, exc, detail)
            return
        self.after(0, self._on_success, out_path)

    def _on_success(self, out_path: Path) -> None:
        self.run_btn.config(state="normal")
        self.status_var.set(f"완료: {out_path}")
        self.status_label.config(foreground="#0a7a0a")
        if messagebox.askyesno(
            APP_TITLE,
            f"완료되었습니다.\n\n결과 파일:\n{out_path.resolve()}\n\n결과 폴더를 열까요?",
        ):
            _open_folder(out_path.parent)

    def _on_error(self, exc: Exception, detail: str) -> None:
        self.run_btn.config(state="normal")
        self.status_var.set("오류 발생")
        self.status_label.config(foreground="#b00020")
        messagebox.showerror(
            APP_TITLE,
            f"실행 중 오류가 발생했습니다.\n\n{type(exc).__name__}: {exc}\n\n"
            f"자세한 내용:\n{detail}",
        )


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
