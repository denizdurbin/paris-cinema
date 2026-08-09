"""Canonical venue catalogue. The single source of truth for venue identity.

Adapters map their own source ids onto these ids; no adapter invents a venue.
AlloCine codes were resolved from allocine.fr/salle/cinema/ville-115755/ on 2026-08-08.
"""

from dataclasses import dataclass
from typing import Literal

Kind = Literal["independent", "chain"]
Coverage = Literal["allocine", "operator", "none"]


@dataclass(frozen=True, slots=True)
class Venue:
    id: str
    name: str
    arrondissement: int
    kind: Kind = "independent"
    chain: str | None = None
    allocine_code: str | None = None
    coverage: Coverage = "allocine"
    dulac_id: str | None = None


def _ind(id, name, arr, code, **kw):
    return Venue(id=id, name=name, arrondissement=arr, allocine_code=code,
                 coverage="allocine" if code else "none", **kw)


def _chain(id, name, arr, chain, code):
    return Venue(id=id, name=name, arrondissement=arr, kind="chain",
                 chain=chain, allocine_code=code, coverage="allocine")


VENUES: tuple[Venue, ...] = (
    # --- independents -----------------------------------------------------
    _ind("jeu-de-paume", "Jeu de Paume", 1, None),
    _ind("luminor-hotel-de-ville", "Luminor Hôtel de Ville", 4, "C0013"),
    _ind("cinema-du-pantheon", "Cinéma du Panthéon", 5, "C0076"),
    _ind("epee-de-bois", "Épée de Bois", 5, None),
    _ind("ecoles-cinema-club", "Écoles Cinéma Club", 5, "C0071"),
    _ind("grand-action", "Le Grand Action", 5, "C0072"),
    _ind("reflet-medicis", "Reflet Médicis", 5, "C0074", dulac_id="583"),
    _ind("studio-galande", "Studio Galande", 5, "C0016"),
    _ind("studio-des-ursulines", "Studio des Ursulines", 5, "C0083"),
    _ind("le-champo", "Le Champo", 5, "C0073"),
    _ind("filmotheque", "La Filmothèque du Quartier Latin", 5, "C0020"),
    _ind("les-3-luxembourg", "Les 3 Luxembourg", 6, "C0095"),
    _ind("arlequin", "L'Arlequin", 6, "C0054", dulac_id="1"),
    _ind("christine-cinema-club", "Christine Cinéma Club", 6, "C0015"),
    _ind("lucernaire", "Lucernaire", 6, "C0093"),
    _ind("nouvel-odeon", "Nouvel Odéon", 6, "C0041"),
    _ind("saint-andre-des-arts", "Saint-André des Arts", 6, "C0100"),
    _ind("saint-germain-des-pres", "Le Saint-Germain des Prés", 6, "C0096"),
    _ind("le-balzac", "Le Balzac", 8, "C0009"),
    _ind("elysees-lincoln", "Les Elysées Lincoln", 8, "C0108"),
    _ind("cinq-caumartin", "5 Caumartin", 9, "C0012"),
    _ind("max-linder", "Max Linder Panorama", 9, "C0089"),
    _ind("archipel", "L'Archipel", 10, "C0134"),
    _ind("le-brady", "Le Brady", 10, "C0023"),
    _ind("louxor", "Louxor", 10, None),
    _ind("majestic-bastille", "Majestic Bastille", 11, "C0139", dulac_id="165"),
    _ind("escurial", "L'Escurial", 13, "C0147", dulac_id="422"),
    _ind("sept-parnassiens", "7 Parnassiens", 14, "C0025"),
    _ind("entrepot", "L'Entrepôt", 14, "C0005"),
    _ind("majestic-passy", "Majestic Passy", 16, "C0120", dulac_id="518"),
    _ind("cinema-des-cineastes", "Cinéma des Cinéastes", 17, "C0004"),
    _ind("club-de-letoile", "Club de l'Étoile", 17, None),
    _ind("le-ciney", "Le CiNey", 18, None),
    _ind("studio-28", "Studio 28", 18, "C0061"),
    # --- chains: UGC ------------------------------------------------------
    _chain("ugc-cine-cite-bercy", "UGC Ciné Cité Bercy", 12, "UGC", "C0026"),
    _chain("ugc-cine-cite-les-halles", "UGC Ciné Cité Les Halles", 1, "UGC", "C0159"),
    _chain("ugc-cine-cite-maillot", "UGC Ciné Cité Maillot", 17, "UGC", "C0175"),
    _chain("ugc-danton", "UGC Danton", 6, "UGC", "C0102"),
    _chain("ugc-gobelins", "UGC Gobelins", 13, "UGC", "C0150"),
    _chain("ugc-lyon-bastille", "UGC Lyon Bastille", 12, "UGC", "C0146"),
    _chain("ugc-montparnasse", "UGC Montparnasse", 6, "UGC", "C0103"),
    _chain("ugc-odeon", "UGC Odéon", 6, "UGC", "C0104"),
    _chain("ugc-opera", "UGC Opéra", 9, "UGC", "C0126"),
    _chain("ugc-rotonde", "UGC Rotonde", 6, "UGC", "C0105"),
    # --- chains: MK2 ------------------------------------------------------
    _chain("mk2-bastille-beaumarchais", "MK2 Bastille (Beaumarchais)", 11, "MK2", "C0140"),
    _chain("mk2-bastille-fg", "MK2 Bastille (Fg St Antoine)", 11, "MK2", "C0040"),
    _chain("mk2-beaubourg", "MK2 Beaubourg", 3, "MK2", "C0050"),
    _chain("mk2-bibliotheque", "MK2 Bibliothèque", 13, "MK2", "C2954"),
    _chain("mk2-gambetta", "MK2 Gambetta", 20, "MK2", "C0192"),
    _chain("mk2-nation", "MK2 Nation", 12, "MK2", "C0144"),
    _chain("mk2-odeon-st-germain", "MK2 Odéon (St Germain)", 6, "MK2", "C0097"),
    _chain("mk2-odeon-st-michel", "MK2 Odéon (St Michel)", 6, "MK2", "C0092"),
    _chain("mk2-quai-de-loire", "MK2 Quai de Loire", 19, "MK2", "C1621"),
    _chain("mk2-quai-de-seine", "MK2 Quai de Seine", 19, "MK2", "C0003"),
)

_BY_ID = {v.id: v for v in VENUES}
_BY_CODE = {v.allocine_code: v for v in VENUES if v.allocine_code}


def by_id(vid: str) -> Venue:
    return _BY_ID[vid]


def by_allocine_code(code: str) -> Venue | None:
    return _BY_CODE.get(code)


def independents() -> tuple[Venue, ...]:
    return tuple(v for v in VENUES if v.kind == "independent")


def chains() -> tuple[Venue, ...]:
    return tuple(v for v in VENUES if v.kind == "chain")
