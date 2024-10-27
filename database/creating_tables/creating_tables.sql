DO $$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lobby_status') THEN
        CREATE TYPE public.lobby_status AS ENUM ('waiting', 'started', 'finished');
    END IF;
IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_status') THEN
        CREATE TYPE public.user_status AS ENUM ('admin', 'player');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS public."lobby" (
        id SERIAL primary key,
        num_players int not null check (num_players >= 0),
        status lobby_status not null default 'waiting',
        round int not null default 0,
        stones_cnt int not null default 0
    );

CREATE TABLE IF NOT EXISTS public."user" (
        id SERIAL primary key,
        tg_id bigint unique not null,
        status user_status not null default 'player',
        current_lobby_id int references public."lobby" (id) ON DELETE SET NULL
    );

select * from public."lobby";
