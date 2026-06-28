"""DTO público y estable del Motor de Catálogo: NormalizedProduct.

Es el contrato que todo conector debe producir y que todo consumidor (Odoo,
portal, e-commerce, móvil, IA) recibe. Tipado y agnóstico al proveedor.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .exceptions import NormalizationError


@dataclass
class NormalizedPrice:
    cost: Optional[float] = None       # costo (lo que nos cuesta al distribuidor)
    list: Optional[float] = None       # precio de lista / MSRP
    map: Optional[float] = None        # precio mínimo anunciado (MAP)
    special: Optional[float] = None    # precio especial/promoción
    currency: str = "USD"


@dataclass
class NormalizedStock:
    total: int = 0
    by_warehouse: Dict[str, int] = field(default_factory=dict)


@dataclass
class NormalizedDocument:
    name: str
    url: str
    kind: str = "datasheet"            # datasheet | manual | certificate | other


@dataclass
class NormalizedProduct:
    """Producto normalizado, independiente del distribuidor. Solo URLs (sin binarios)."""
    backend_key: str
    external_ref: str
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    description: Optional[str] = None
    attributes: List[str] = field(default_factory=list)   # características/especificaciones
    category_path: List[str] = field(default_factory=list)
    price: NormalizedPrice = field(default_factory=NormalizedPrice)
    stock: NormalizedStock = field(default_factory=NormalizedStock)
    images: List[str] = field(default_factory=list)       # URLs (CDN del proveedor)
    image_360: Optional[str] = None
    documents: List[NormalizedDocument] = field(default_factory=list)
    sat_key: Optional[str] = None
    sat_unit: Optional[str] = None
    warranty: Optional[str] = None
    dimensions: Dict[str, float] = field(default_factory=dict)   # {alto,ancho,largo,volumen}
    weight: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict)            # payload crudo (caché/depuración)

    def __post_init__(self):
        if not self.backend_key:
            raise NormalizationError("NormalizedProduct sin backend_key")
        if not self.external_ref:
            raise NormalizationError("NormalizedProduct sin external_ref")
        if not self.name:
            raise NormalizationError("NormalizedProduct sin name (ref=%s)" % self.external_ref)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
