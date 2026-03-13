from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text


class AgentDisplay:
    def __init__(self):
        self._console = Console()
        self._log_lines: list[str] = []
        self._message_lines: list[str] = []
        self._tokens_in: int = 0
        self._tokens_out: int = 0
        self._price: float = 0.0
        self._local_tokens_in: int = 0
        self._local_tokens_out: int = 0
        self._actions: list[str] = []
        self._current_action: int = -1

    def log(self, text: str) -> None:
        self._log_lines.append(text)
        self.refresh()

    def message(self, text: str) -> None:
        if "\n" in text:
            text = text.split("\n")
            for line in text:
                self._message_lines.append(line)
        else:
            self._message_lines.append(text)
        self.refresh()

    def stats(self, tokens_in: int, tokens_out: int, price: float | None) -> None:
        if price is None:
            self._local_tokens_in = tokens_in
            self._local_tokens_out = tokens_out
        else:
            self._tokens_in = tokens_in
            self._tokens_out = tokens_out
            self._price = price
        self.refresh()

    def set_actions(self, actions: list[str]) -> None:
        self._actions = list(actions)
        self._current_action = -1
        self.refresh()

    def move_action(self, index: int) -> None:
        self._current_action = index
        self.refresh()

    def next_action(self) -> None:
        self._current_action = self._current_action + 1
        self.refresh()

    def _tail(self, lines: list[str], max_rows: int, width: int = 0) -> str:
        if max_rows <= 0 or not lines:
            return ""
        if width <= 0:
            return "\n".join(lines[-max_rows:])
        rows_used = 0
        selected: list[str] = []
        for line in reversed(lines):
            line_rows = max(1, (len(line) + width - 1) // width)
            if rows_used + line_rows > max_rows and selected:
                break
            selected.append(line)
            rows_used += line_rows
        selected.reverse()
        return "\n".join(selected)

    def _styled_tail(self, lines: list[str], max_lines: int, style: str, width: int = 0) -> Text:
        raw = self._tail(lines, max_lines, width)
        return Text(raw, style=style)

    def _render_actions(self) -> Text:
        text = Text()
        for i, action in enumerate(self._actions):
            if i > 0:
                text.append("\n")
            if i < self._current_action:
                text.append(action, style="grey37")
            elif i == self._current_action:
                text.append(action, style="bold bright_yellow")
            else:
                text.append(action, style="white")
        return text

    def refresh(self) -> None:
        height = self._console.size.height
        width = self._console.size.width

        upper_h = ((height - 2) * 2) // 3
        lower_h = height - 2 - upper_h

        log_avail = max(0, lower_h - 2)
        msg_avail = max(0, upper_h - 2)

        msg_panel_w = max(1, (width * 2) // 3 - 2)
        log_panel_w = max(1, width - 2)

        stats_text = Text()
        stats_text.append("   Tokeny IN: ", style="grey62")
        stats_text.append(f"{self._tokens_in}\n", style="white")
        stats_text.append("  Tokeny OUT: ", style="grey62")
        stats_text.append(f"{self._tokens_out}\n", style="white")
        stats_text.append("    Cena USD: ", style="grey62")
        stats_text.append(f"{self._price:.4f}\n", style="white")
        stats_text.append("\n")
        stats_text.append("  Lokalne IN: ", style="grey62")
        stats_text.append(f"{self._local_tokens_in}\n", style="white")
        stats_text.append(" Lokalne OUT: ", style="grey62")
        stats_text.append(f"{self._local_tokens_out}", style="white")

        layout = Layout()
        layout.split_column(
            Layout(name="spacer", size=2),
            Layout(name="upper", ratio=2),
            Layout(name="lower", ratio=1),
        )
        layout["upper"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=2),
        )
        layout["left"].split_column(
            Layout(name="action", ratio=3),
            Layout(name="stats", ratio=1),
        )

        BORDER = "dark_green"
        TITLE = "green"

        layout["spacer"].update("")
        layout["action"].update(
            Panel(self._render_actions(), title=f"[{TITLE}]Akcja[/]", border_style=BORDER)
        )
        layout["stats"].update(
            Panel(stats_text, title=f"[{TITLE}]Statystyki[/]", border_style=BORDER)
        )
        layout["right"].update(
            Panel(
                self._tail(self._message_lines, msg_avail, msg_panel_w),
                title=f"[{TITLE}]Wiadomości[/]",
                border_style=BORDER,
            )
        )
        layout["lower"].update(
            Panel(
                self._styled_tail(self._log_lines, log_avail, "grey62", log_panel_w),
                title=f"[{TITLE}]Logi[/]",
                border_style=BORDER,
            )
        )

        self._console.clear()
        self._console.print(layout)
