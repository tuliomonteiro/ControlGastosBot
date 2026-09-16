-- The bot gained a 'Bebê' category but the system categories were seeded without
-- it, so mirrored expenses fell back to 'Uncategorized'.
insert into public.categories (name, slug)
values ('Bebê', 'bebe')
on conflict do nothing;
