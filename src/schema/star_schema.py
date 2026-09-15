"""Dataclasses describing the fact/dimension tables of the warehouse star schema."""

from dataclasses import dataclass


@dataclass
class DimTable:
    name: str
    columns: list[str]


@dataclass
class FactTable:
    name: str
    columns: list[str]
    foreign_keys: list[str]
