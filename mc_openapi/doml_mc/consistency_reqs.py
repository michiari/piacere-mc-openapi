from z3 import (
    Const, Consts, ExprRef, Solver,
    Exists, ForAll, Implies, And, Or, Not
)

from .intermediate_model import MetaModel
from .intermediate_model.metamodel import get_subclasses_dict
from .imc import (
    SMTEncoding, SMTSorts, Requirement, RequirementStore
)
from .z3encoding.utils import Iff


def subclass_cond(smtenc: SMTEncoding, subclasses: set[str], elem: ExprRef) -> ExprRef:
    return Or(
        *(
            smtenc.element_class_fun(elem) == smtenc.classes[scname]
            for scname in subclasses
        )
    )


def get_attribute_type_reqs(mm: MetaModel) -> RequirementStore:
    subclasses_dict = get_subclasses_dict(mm)
    # A type validity constraint is added for every attribute:
    reqs: list[Requirement] = []
    for cname, c in mm.items():
        for mm_attr in c.attributes.values():
            # For all source elements and attribute data, their classes must be
            # a subtype of the source class, and the data must be of the data
            # type of the attribute.
            def req_assertion(smtenc: SMTEncoding, smtsorts: SMTSorts, cname=cname, mm_attr=mm_attr) -> ExprRef:
                elem = Const("elem", smtsorts.element_sort)
                attr_val = Const("attr_val", smtsorts.attr_data_sort)
                src_subclass_cond = subclass_cond(smtenc, subclasses_dict[cname], elem)  # Source subclass condition
                if mm_attr.type == "Boolean":
                    tgt_type_cond = smtsorts.attr_data_sort.is_bool(attr_val)  # type: ignore
                elif mm_attr.type == "Integer":
                    tgt_type_cond = smtsorts.attr_data_sort.is_int(attr_val)  # type: ignore
                elif mm_attr.type == "String":
                    tgt_type_cond = smtsorts.attr_data_sort.is_ss(attr_val)  # type: ignore
                else:  # mm_attr.type == "GeneratorKind"
                    tgt_type_cond = Or(
                        attr_val == smtsorts.attr_data_sort.ss(smtenc.str_symbols["IMAGE"]),  # type: ignore
                        attr_val == smtsorts.attr_data_sort.ss(smtenc.str_symbols["SCRIPT"]),  # type: ignore
                    )
                return Exists(
                    [elem, attr_val],
                    And(
                        smtenc.attribute_rel(elem, smtenc.attributes[f"{cname}::{mm_attr.name}"], attr_val),
                        Or(
                            Not(src_subclass_cond),
                            Not(tgt_type_cond),
                        ),
                    ),
                )

            reqs.append(
                Requirement(
                    req_assertion,
                    f"attribute_st_types {cname}::{mm_attr.name}",
                    f"Attribute {mm_attr.name} from class {cname} must have type {mm_attr.type}.",
                    f"Attribute {mm_attr.name} from class {cname} has a type different from {mm_attr.type}.",
                )
            )
    return RequirementStore(reqs)


def get_attribute_multiplicity_reqs(mm: MetaModel) -> RequirementStore:
    subclasses_dict = get_subclasses_dict(mm)
    # A multiplicity constraint is added for every attribute:
    reqs: list[Requirement] = []
    for cname, c in mm.items():
        for mm_attr in c.attributes.values():
            def req_assertion_lb(smtenc: SMTEncoding, smtsorts: SMTSorts, cname=cname, mm_attr=mm_attr) -> ExprRef:
                elem = Const("elem", smtsorts.element_sort)
                attr_val = Const("attr_val", smtsorts.attr_data_sort)
                src_subclass_cond = subclass_cond(smtenc, subclasses_dict[cname], elem)  # Source subclass condition
                return Exists(
                    [elem],
                    And(
                        src_subclass_cond,
                        Not(
                            Exists(
                                [attr_val],
                                smtenc.attribute_rel(elem, smtenc.attributes[f"{cname}::{mm_attr.name}"], attr_val),
                            ),
                        )
                    ),
                )

            def req_assertion_ub(smtenc: SMTEncoding, smtsorts: SMTSorts, cname=cname, mm_attr=mm_attr) -> ExprRef:
                elem = Const("elem", smtsorts.element_sort)
                attr_val1, attr_val2 = Consts("attr_val1 attr_val2", smtsorts.attr_data_sort)
                return Exists(
                    [elem, attr_val1, attr_val2],
                    And(
                        smtenc.attribute_rel(elem, smtenc.attributes[f"{cname}::{mm_attr.name}"], attr_val1),
                        smtenc.attribute_rel(elem, smtenc.attributes[f"{cname}::{mm_attr.name}"], attr_val2),
                        attr_val1 != attr_val2,
                    ),
                )

            lb, ub = mm_attr.multiplicity
            if lb == "1":
                reqs.append(
                    Requirement(
                        req_assertion_lb,
                        f"attribute_mult_lb {cname}::{mm_attr.name}",
                        f"Attribute {mm_attr.name} from class {cname} must have at least one value.",
                        f"Mandatory attribute {mm_attr.name} from class {cname} has no value.",
                    )
                )
            if ub == "1":
                reqs.append(
                    Requirement(
                        req_assertion_ub,
                        f"attribute_mult_ub {cname}::{mm_attr.name}",
                        f"Attribute {mm_attr.name} from class {cname} must have at most one value.",
                        f"Attribute {mm_attr.name} from class {cname} has more than one value.",
                    )
                )
    return RequirementStore(reqs)


def get_association_type_reqs(mm: MetaModel) -> RequirementStore:
    subclasses_dict = get_subclasses_dict(mm)
    # A type validity constraint is added for every association:
    reqs: list[Requirement] = []
    for cname, c in mm.items():
        for mm_assoc in c.associations.values():
            # For all source and target elements that are associated, their
            # classes must be a subtype of the source and target classes resp.
            # of the association.
            def req_assertion(smtenc: SMTEncoding, smtsorts: SMTSorts, cname=cname, mm_assoc=mm_assoc) -> ExprRef:
                es, et = Consts("es et", smtsorts.element_sort)
                return Exists(
                    [es, et],
                    And(
                        smtenc.association_rel(es, smtenc.associations[f"{cname}::{mm_assoc.name}"], et),
                        Not(
                            And(
                                subclass_cond(smtenc, subclasses_dict[cname], es),  # Source subclass condition
                                subclass_cond(smtenc, subclasses_dict[mm_assoc.class_], et)  # Target subclass condition
                            ),
                        ),
                    ),
                )

            reqs.append(
                Requirement(
                    req_assertion,
                    f"association_st_classes {cname}::{mm_assoc.name}",
                    f"Association {mm_assoc.name} from class {cname} must target class {mm_assoc.class_}.",
                    f"Association {mm_assoc.name} from class {cname} has a class different from {mm_assoc.class_}.",
                )
            )
    return RequirementStore(reqs)


def get_association_multiplicity_reqs(mm: MetaModel) -> RequirementStore:
    subclasses_dict = get_subclasses_dict(mm)
    # A multiplicity constraint is added for every association:
    reqs: list[Requirement] = []
    for cname, c in mm.items():
        for mm_assoc in c.associations.values():
            def req_assertion_lb(smtenc: SMTEncoding, smtsorts: SMTSorts, cname=cname, mm_assoc=mm_assoc) -> ExprRef:
                es, et = Consts("es et", smtsorts.element_sort)
                return Exists(
                    [es],
                    And(
                        subclass_cond(smtenc, subclasses_dict[cname], es),  # Source subclass condition
                        Not(
                            Exists(
                                [et],
                                smtenc.association_rel(es, smtenc.associations[f"{cname}::{mm_assoc.name}"], et),
                            ),
                        )
                    ),
                )

            def req_assertion_ub(smtenc: SMTEncoding, smtsorts: SMTSorts, cname=cname, mm_assoc=mm_assoc) -> ExprRef:
                es, et1, et2 = Consts("es et1 et2", smtsorts.element_sort)
                return Exists(
                    [es, et1, et2],
                    And(
                        smtenc.association_rel(es, smtenc.associations[f"{cname}::{mm_assoc.name}"], et1),
                        smtenc.association_rel(es, smtenc.associations[f"{cname}::{mm_assoc.name}"], et2),
                        et1 != et2,
                    ),
                )

            lb, ub = mm_assoc.multiplicity
            if lb == "1":
                reqs.append(
                    Requirement(
                        req_assertion_lb,
                        f"association_mult_lb {cname}::{mm_assoc.name}",
                        f"Association {mm_assoc.name} from class {cname} must have at least one target.",
                        f"Mandatory association {mm_assoc.name} is missing from an element of class {cname}.",
                    )
                )
            if ub == "1":
                reqs.append(
                    Requirement(
                        req_assertion_ub,
                        f"association_mult_ub {cname}::{mm_assoc.name}",
                        f"Association {mm_assoc.name} from class {cname} must have at most one target.",
                        f"Association {mm_assoc.name} has more than one target in an element of class {cname}.",
                    )
                )
    return RequirementStore(reqs)


def get_inverse_association_reqs(inv_assoc: list[tuple[str, str]]) -> RequirementStore:
    # Inverse association assertions
    reqs: list[Requirement] = []
    for an1, an2 in inv_assoc:
        def req_assertion(smtenc: SMTEncoding, smtsorts: SMTSorts, an1=an1, an2=an2) -> ExprRef:
            es, et = Consts("es et", smtsorts.element_sort)
            return Exists(
                [es, et],
                Not(
                    Iff(
                        smtenc.association_rel(es, smtenc.associations[an1], et),
                        smtenc.association_rel(et, smtenc.associations[an2], es)
                    ),
                )
            )

        reqs.append(
            Requirement(
                req_assertion,
                f"association_inverse {an1} {an2}",
                f"Association {an1} must be the inverse of {an2}.",
                f"Association {an1} is not the inverse of {an2}.",
            )
        )
    return RequirementStore(reqs)


def assert_attribute_rel_constraints(
    mm: MetaModel,
    solver: Solver,
    smtenc: SMTEncoding,
    smtsorts: SMTSorts
):
    subclasses_dict = get_subclasses_dict(mm)
    es = Const("es", smtsorts.element_sort)
    ad, ad_ = Consts("ad ad_", smtsorts.attr_data_sort)
    # A type validity constraint is added for every attribute:
    for cname, c in mm.items():
        src_subclass_cond = Or(  # Source subclass condition
            *(
                smtenc.element_class_fun(es) == smtenc.classes[scname]
                for scname in subclasses_dict[cname]
            )
        )
        for mm_attr in c.attributes.values():
            # For all source elements and attribute data, their classes must be
            # a subtype of the source class, and the data must be of the data
            # type of the attribute.
            if mm_attr.type == "Boolean":
                tgt_type_cond = smtsorts.attr_data_sort.is_bool(ad)  # type: ignore
            elif mm_attr.type == "Integer":
                tgt_type_cond = smtsorts.attr_data_sort.is_int(ad)  # type: ignore
            elif mm_attr.type == "String":
                tgt_type_cond = smtsorts.attr_data_sort.is_ss(ad)  # type: ignore
            else:  # mm_attr.type == "GeneratorKind"
                tgt_type_cond = Or(
                    ad == smtsorts.attr_data_sort.ss(smtenc.str_symbols["IMAGE"]),  # type: ignore
                    ad == smtsorts.attr_data_sort.ss(smtenc.str_symbols["SCRIPT"]),  # type: ignore
                )
            assn = ForAll(
                [es, ad],
                Implies(
                    smtenc.attribute_rel(es, smtenc.attributes[f"{cname}::{mm_attr.name}"], ad),
                    And(
                        src_subclass_cond,
                        tgt_type_cond,
                    ),
                ),
            )
            solver.assert_and_track(assn, f"attribute_st_types {cname}::{mm_attr.name}")

            # Multiplicity constraints
            lb, ub = mm_attr.multiplicity
            if lb == "1":
                mult_lb_assn = ForAll(
                    [es],
                    Implies(
                        src_subclass_cond,
                        Exists(
                            [ad],
                            smtenc.attribute_rel(es, smtenc.attributes[f"{cname}::{mm_attr.name}"], ad),
                        ),
                    ),
                )
                solver.assert_and_track(
                    mult_lb_assn,
                    f"attribute_mult_lb {cname}::{mm_attr.name}",
                )
            if ub == "1":
                mult_ub_assn = ForAll(
                    [es, ad, ad_],
                    Implies(
                        And(
                            smtenc.attribute_rel(es, smtenc.attributes[f"{cname}::{mm_attr.name}"], ad),
                            smtenc.attribute_rel(
                                es, smtenc.attributes[f"{cname}::{mm_attr.name}"], ad_
                            ),
                        ),
                        ad == ad_,
                    ),
                )
                solver.assert_and_track(
                    mult_ub_assn,
                    f"attribute_mult_ub {cname}::{mm_attr.name}",
                )


def assert_association_rel_constraints(
    mm: MetaModel,
    inv_assoc: list[tuple[str, str]],
    solver: Solver,
    smtenc: SMTEncoding,
    smtsorts: SMTSorts
):
    subclasses_dict = get_subclasses_dict(mm)
    es, et, et_ = Consts("es et et_", smtsorts.element_sort)
    # A type validity constraint is added for every association:
    for cname, c in mm.items():
        src_subclass_cond = Or(  # Source subclass condition
            *(
                smtenc.element_class_fun(es) == smtenc.classes[scname]
                for scname in subclasses_dict[cname]
            )
        )
        for mm_assoc in c.associations.values():
            # For all source and target elements that are associated, their
            # classes must be a subtype of the source and target classes resp.
            # of the association.
            class_assn = ForAll(
                [es, et],
                Implies(
                    smtenc.association_rel(es, smtenc.associations[f"{cname}::{mm_assoc.name}"], et),
                    And(
                        src_subclass_cond,
                        Or(  # Target subclass condition
                            *(
                                smtenc.element_class_fun(et) == smtenc.classes[scname]
                                for scname in subclasses_dict[mm_assoc.class_]
                            )
                        ),
                    ),
                ),
            )
            solver.assert_and_track(
                class_assn, f"association_st_classes {cname}::{mm_assoc.name}"
            )

            # Multiplicity constraints
            lb, ub = mm_assoc.multiplicity
            if lb == "1":
                mult_lb_assn = ForAll(
                    [es],
                    Implies(
                        src_subclass_cond,
                        Exists(
                            [et],
                            smtenc.association_rel(
                                es, smtenc.associations[f"{cname}::{mm_assoc.name}"], et
                            ),
                        ),
                    ),
                )
                solver.assert_and_track(
                    mult_lb_assn,
                    f"association_mult_lb {cname}::{mm_assoc.name}",
                )
            if ub == "1":
                mult_ub_assn = ForAll(
                    [es, et, et_],
                    Implies(
                        And(
                            smtenc.association_rel(
                                es, smtenc.associations[f"{cname}::{mm_assoc.name}"], et
                            ),
                            smtenc.association_rel(
                                es, smtenc.associations[f"{cname}::{mm_assoc.name}"], et_
                            ),
                        ),
                        et == et_,
                    ),
                )
                solver.assert_and_track(
                    mult_ub_assn,
                    f"association_mult_ub {cname}::{mm_assoc.name}",
                )

    # Inverse association assertions
    for an1, an2 in inv_assoc:
        inv_assn = ForAll(
            [es, et],
            Iff(smtenc.association_rel(es, smtenc.associations[an1], et), smtenc.association_rel(et, smtenc.associations[an2], es)),
        )
        solver.assert_and_track(inv_assn, f"association_inverse {an1} {an2}")
