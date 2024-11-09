DO $$
BEGIN
IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lobby_status') THEN
        CREATE TYPE public.lobby_status AS ENUM ('waiting', 'started', 'finished', 'created');
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
        default_stones_cnt int not null default 0,
        current_stones_cnt int not null default 0,
        move_max_duration_ms int not null default 15,
        round_duration_ms int not null default 120
    );

CREATE TABLE IF NOT EXISTS public."user" (
        id SERIAL primary key,
        tg_id bigint unique not null,
        status user_status not null default 'player',
        current_lobby_id int references public."lobby" (id) ON DELETE SET NULL
    );