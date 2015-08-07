/* Users and Aquaponics systems */
create table if not exists users (id integer primary key not null auto_increment, google_id varchar(100) not null, email varchar(100) not null);
create table if not exists systems (id integer primary key not null auto_increment, user_id integer not null references users, name varchar(100) not null, system_id varchar(40) not null, creation_time timestamp not null);

/* Meeasurement data */
create table if not exists o2_measurements (id integer primary key not null auto_increment, system_id integer references systems, time timestamp not null, value decimal(13,10));
create table if not exists ph_measurements (id integer primary key not null auto_increment, system_id integer references systems, time timestamp not null, value decimal(13,10));
create table if not exists temp_measurements (id integer primary key not null auto_increment, system_id integer references systems, time timestamp not null, value decimal(13,10));
create table if not exists nitrate_measurements (id integer primary key not null auto_increment, system_id integer references systems, time timestamp not null, value decimal(13,10));
create table if not exists ammonium_measurements (id integer primary key not null auto_increment, system_id integer references systems, time timestamp not null, value decimal(13,10));
create table if not exists light_measurements (id integer primary key not null auto_increment, system_id integer references systems, time timestamp not null, value decimal(13,10));

alter table o2_measurements add unique unique_o2meas_systime (system_id, time);
alter table ph_measurements add unique unique_phmeas_systime (system_id, time);
alter table temp_measurements add unique unique_tempmeas_systime (system_id, time);
alter table nitrate_measurements add unique unique_nitrmeas_systime (system_id, time);
alter table ammonium_measurements add unique unique_ammomeas_systime (system_id, time);
alter table light_measurements add unique unique_lightmeas_systime (system_id, time);

