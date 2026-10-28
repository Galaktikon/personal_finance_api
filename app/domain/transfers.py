from decimal import Decimal

from app.domain.transactions import TransactionKind, validate_transaction


def validate_transfer_pair(
    source_amount: Decimal,
    destination_amount: Decimal,
    source_kind: TransactionKind,
    destination_kind: TransactionKind,
    source_account_id: object,
    destination_account_id: object,
) -> None:
    if source_account_id == destination_account_id:
        raise ValueError("Transfer accounts must differ")
    if source_kind is not TransactionKind.TRANSFER_OUT:
        raise ValueError("Source transaction must be transfer_out")
    if destination_kind is not TransactionKind.TRANSFER_IN:
        raise ValueError("Destination transaction must be transfer_in")
    outgoing = validate_transaction(source_amount, source_kind)
    incoming = validate_transaction(destination_amount, destination_kind)
    if outgoing + incoming != 0:
        raise ValueError("Transfer amounts must cancel")
