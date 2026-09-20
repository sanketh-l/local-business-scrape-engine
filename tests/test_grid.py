from leadgen.db import connect, init_db
from leadgen.config import load_config
from leadgen.grid import generate_grid


def test_generate_grid(tmp_path):
    db_path = tmp_path / "test.sqlite"
    init_db(db_path)
    with connect(db_path) as conn:
        load_config(conn, "configs/categories.yaml", "configs/locations.yaml")
        count = generate_grid(conn, "austin_tx", "configs/grid_profiles.yaml")
        stored = conn.execute("SELECT COUNT(*) count FROM grid_cells").fetchone()["count"]
    assert count > 0
    assert stored == count
