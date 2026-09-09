-- Hand-authored data migration. Existing amounts have two decimal places.
UPDATE invoices SET cents = CAST(amount AS INTEGER) * 100;
