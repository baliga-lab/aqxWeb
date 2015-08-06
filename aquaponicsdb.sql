/* Users and Aquaponics systems */
create table if not exists users (id integer primary key not null auto_increment, google_id varchar(100) not null, email varchar(100) not null);
create table if not exists systems (id integer primary key not null auto_increment, user_id integer not null references users, name varchar(100) not null, system_id varchar(40) not null);

/* Meeasurement data */
create table if not exists submissions (id integer primary key not null auto_increment, system_id integer not null references systems, time timestamp not null);
create table if not exists measurements (id integer primary key not null auto_increment, system_id integer references systems, submission_id integer references sumbmissions, time timestamp not null, temperature decimal(13,10), ph decimal(13,10), ammonium decimal(13,10), nitrate decimal(13,10), oxygen decimal(13,10), light decimal(13,10));
