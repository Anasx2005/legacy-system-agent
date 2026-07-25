from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models.model_element_index import ModelElementIndex


def upsert_model_element(
    db: Session,
    system_id: int,
    git_path: str,
    layer: str,
    archimate_type: str,
    name: str,
    current_commit: str | None = None,
) -> ModelElementIndex:

    statement = select(ModelElementIndex).where(
        ModelElementIndex.system_id == system_id,
        ModelElementIndex.git_path == git_path,
    )

    result = db.execute(statement)

    element = result.scalar_one_or_none()

    if element is None:

        element = ModelElementIndex(
            system_id=system_id,
            git_path=git_path,
            layer=layer,
            archimate_type=archimate_type,
            name=name,
            current_commit=current_commit,
            updated_at=datetime.now(UTC),
        )

        db.add(element)

    else:

        element.layer = layer
        element.archimate_type = archimate_type
        element.name = name
        element.current_commit = current_commit
        element.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(element)

    return element


