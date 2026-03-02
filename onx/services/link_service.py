from sqlalchemy import select
from sqlalchemy.orm import Session

from onx.db.models.link import Link
from onx.db.models.link_endpoint import LinkEndpoint, LinkSide
from onx.db.models.node import Node
from onx.db.models.node_capability import NodeCapability
from onx.drivers.registry import get_driver
from onx.schemas.links import LinkCreate


class LinkService:
    def create_link(self, db: Session, payload: LinkCreate) -> Link:
        if payload.left_node_id == payload.right_node_id:
            raise ValueError("left_node_id and right_node_id must be different")

        existing = db.scalar(select(Link).where(Link.name == payload.name))
        if existing is not None:
            raise ValueError(f"Link with name '{payload.name}' already exists.")

        left_node = db.get(Node, payload.left_node_id)
        right_node = db.get(Node, payload.right_node_id)
        if left_node is None or right_node is None:
            raise ValueError("Both left and right nodes must exist.")

        link = Link(
            name=payload.name,
            driver_name=payload.driver_name.value,
            topology_type=payload.topology_type.value,
            left_node_id=payload.left_node_id,
            right_node_id=payload.right_node_id,
            desired_spec_json=payload.spec.model_dump(),
        )
        db.add(link)
        db.flush()

        left_endpoint = LinkEndpoint(
            link_id=link.id,
            node_id=payload.left_node_id,
            side=LinkSide.LEFT,
            interface_name=payload.spec.left.interface_name,
            listen_port=payload.spec.left.listen_port,
            address_v4=payload.spec.left.address_v4,
            address_v6=payload.spec.left.address_v6,
            mtu=payload.spec.left.mtu,
            endpoint=f"{payload.spec.left.endpoint_host}:{payload.spec.left.listen_port}",
        )
        right_endpoint = LinkEndpoint(
            link_id=link.id,
            node_id=payload.right_node_id,
            side=LinkSide.RIGHT,
            interface_name=payload.spec.right.interface_name,
            listen_port=payload.spec.right.listen_port,
            address_v4=payload.spec.right.address_v4,
            address_v6=payload.spec.right.address_v6,
            mtu=payload.spec.right.mtu,
            endpoint=f"{payload.spec.right.endpoint_host}:{payload.spec.right.listen_port}",
        )
        db.add(left_endpoint)
        db.add(right_endpoint)
        db.commit()
        db.refresh(link)
        return link

    def validate_link(self, db: Session, link: Link) -> dict:
        left_capabilities = list(
            db.scalars(
                select(NodeCapability).where(NodeCapability.node_id == link.left_node_id)
            ).all()
        )
        right_capabilities = list(
            db.scalars(
                select(NodeCapability).where(NodeCapability.node_id == link.right_node_id)
            ).all()
        )

        driver = get_driver(link.driver_name)
        result = driver.validate(
            link.desired_spec_json,
            {
                "left_capabilities": [
                    {
                        "capability_name": capability.capability_name,
                        "supported": capability.supported,
                        "details_json": capability.details_json,
                    }
                    for capability in left_capabilities
                ],
                "right_capabilities": [
                    {
                        "capability_name": capability.capability_name,
                        "supported": capability.supported,
                        "details_json": capability.details_json,
                    }
                    for capability in right_capabilities
                ],
            },
        )
        result["capabilities"] = {
            "left": left_capabilities,
            "right": right_capabilities,
        }
        return result
