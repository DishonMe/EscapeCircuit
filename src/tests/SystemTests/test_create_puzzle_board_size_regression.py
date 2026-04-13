from pathlib import Path


# Navigate from test file to project root (up 4 levels: SystemTests -> tests -> src -> Project -> root)
ROOT = Path(__file__).parent.parent.parent.parent


class TestCreatePuzzleBoardSizeRegression:
    def test_create_puzzle_page_uses_current_consts_as_defaults(self):
        source = (ROOT / "apps/nextjs-app/src/app/app/create-puzzle/page.tsx").read_text(encoding='utf-8')

        assert "const DEFAULT_BOARD_ROWS = 15;" in source
        assert "const DEFAULT_BOARD_COLS = 30;" in source
        assert "boardRows: DEFAULT_BOARD_ROWS," in source
        assert "boardCols: DEFAULT_BOARD_COLS," in source

    def test_create_puzzle_page_passes_custom_board_size_to_grid_and_payload(self):
        source = (ROOT / "apps/nextjs-app/src/app/app/create-puzzle/page.tsx").read_text(encoding='utf-8')

        assert "rows: data.basic.boardRows," in source
        assert "cols: data.basic.boardCols," in source
        assert "boardRows={data.basic.boardRows}" in source
        assert "boardCols={data.basic.boardCols}" in source

    def test_workstation_grid_keeps_defaults_when_no_board_size_is_passed(self):
        source = (ROOT / "apps/nextjs-app/src/app/app/puzzles/[id]/_components/workstation-grid.tsx").read_text(encoding='utf-8')

        assert "const DEFAULT_GRID_ROWS = 15;" in source
        assert "const DEFAULT_GRID_COLS = 30;" in source
        assert "boardRows ?? DEFAULT_GRID_ROWS" in source
        assert "boardCols ?? DEFAULT_GRID_COLS" in source
