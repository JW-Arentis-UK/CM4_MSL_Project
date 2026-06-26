from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("cm4_v3link.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()

