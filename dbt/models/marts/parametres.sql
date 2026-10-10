-- Paramètres globaux exposés à Power BI (remplace TODAY() / NOW())
select {{ as_of() }} as date_reference, current_timestamp as date_actualisation
