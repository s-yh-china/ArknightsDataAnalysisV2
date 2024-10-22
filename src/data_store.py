from pathlib import Path

root_path = Path(__file__).parents[1]


def get_res_path(_path: str | list[str] | None = None) -> Path:
    if _path:
        if isinstance(_path, str):
            path = root_path / _path
        else:
            path = root_path.joinpath(*_path)
    else:
        path = root_path

    if not path.exists():
        path.mkdir(parents=True)

    return path
