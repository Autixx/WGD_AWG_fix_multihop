from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from onx.api.deps import get_database_session
from onx.db.models.node import Node
from onx.schemas.nodes import NodeCreate, NodeRead, NodeUpdate


router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("", response_model=list[NodeRead])
def list_nodes(db: Session = Depends(get_database_session)) -> list[Node]:
    return list(db.scalars(select(Node).order_by(Node.created_at.desc())).all())


@router.post("", response_model=NodeRead, status_code=status.HTTP_201_CREATED)
def create_node(payload: NodeCreate, db: Session = Depends(get_database_session)) -> Node:
    existing = db.scalar(select(Node).where(Node.name == payload.name))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Node with name '{payload.name}' already exists.",
        )

    node = Node(**payload.model_dump())
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


@router.get("/{node_id}", response_model=NodeRead)
def get_node(node_id: str, db: Session = Depends(get_database_session)) -> Node:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found.")
    return node


@router.patch("/{node_id}", response_model=NodeRead)
def update_node(node_id: str, payload: NodeUpdate, db: Session = Depends(get_database_session)) -> Node:
    node = db.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found.")

    if payload.name and payload.name != node.name:
        existing = db.scalar(select(Node).where(Node.name == payload.name))
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Node with name '{payload.name}' already exists.",
            )

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(node, key, value)

    db.add(node)
    db.commit()
    db.refresh(node)
    return node
