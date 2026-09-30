-- Service-role RPC to create or rotate named Vault secrets.
-- Called by scripts/put_vault_secret.py (not the Supabase CLI `secrets` command,
-- which is for Edge Functions).

create or replace function public.put_app_secret(secret_name text, secret_value text)
returns void
language plpgsql
security definer
set search_path = vault, public, pg_temp
as $$
declare
    secret_id uuid;
begin
    if coalesce(auth.role(), current_user) not in ('service_role', 'postgres', 'supabase_admin') then
        raise exception 'not authorized to write vault secrets';
    end if;

    if secret_name is null or secret_name = '' or secret_value is null or secret_value = '' then
        raise exception 'secret name and value are required';
    end if;

    select id
      into secret_id
      from vault.secrets
     where name = secret_name
     limit 1;

    if secret_id is null then
        perform vault.create_secret(secret_value, secret_name);
    else
        perform vault.update_secret(secret_id, secret_value);
    end if;
end;
$$;

revoke all on function public.put_app_secret(text, text) from public, anon, authenticated;
grant execute on function public.put_app_secret(text, text) to service_role, postgres;
