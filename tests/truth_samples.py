"""Made-up event files for tests. Never put a real supplier file in the repo: they name minors."""

EYEBALL_SAMPLE = (
    "ID;Half;Event;Player;Team;Video time;Football time;X coordinate;Y coordinate;Details\n"
    '1;1st half;pass;9. Test PLAYER;Alpha;30.0;0;0.5;0.5;{"outcome":"success","restart":"no"}\n'
    '2;1st half;pass_received;7. Next PLAYER;Alpha;31.5;1;0.6;0.4;{"outcome":"success"}\n'
    '3;1st half;pass;4. Other PLAYER;Beta;95.2;65;0.99;0.02;{"outcome":"fail","restart":"corner-kick"}\n'
    '4;1st half;shot;9. Test PLAYER;Alpha;120.0;90;0.9;0.5;{"outcome":"success","on_target":"on","restart":"no","xg":0.3}\n'
    '5;1st half;goal;9. Test PLAYER;Alpha;121.0;91;0.9;0.5;{"goal_type":"open_play"}\n'
    "6;1st half;goal_conceded;-. - -;Beta;121.0;91;0.1;0.5;{}\n"
    '7;1st half;pass;-. - -;Beta;180.0;150;0.5;0.5;{"outcome":"success","restart":"no"}\n'
    '8;1st half;pass;-. - -;Beta;200,5;170;0.3;1.0;{"outcome":"success","restart":"throw-in"}\n'
    '9;2nd half;pass;-. - -;Beta;3000.0;2700;0.5;0.5;{"outcome":"success","restart":"no"}\n'
    '10;2nd half;shot;-. - -;Alpha;3100.0;2800;0.95;0.5;{"outcome":"fail","on_target":"off","restart":"penalty-kick"}\n'
    '11;2nd half;pass;-. - -;Alpha;3200.0;2900;0.1;0.5;{"outcome":"success","restart":"goal-kick"}\n'
    "12;2nd half;pass;-. - -;Beta;;;;;{}\n"
)

# The same file without its one untimed row.
EYEBALL_TIMED = "".join(EYEBALL_SAMPLE.splitlines(keepends=True)[:-1])

STATPADDER_SAMPLE = (
    "period,clock,match_minute,type,team,side,third,x,y,end_x,end_y,player_number,player_name,"
    "flagged,confidence,logged_at,xg,video_ms,outcome,penalty\n"
    "First half,01:05,2,corner,Us,own,final,0.99,0.02,,,7,Test Player,false,,2026-10-01T10:00:00Z,,65000,,\n"
    "First half,05:00,6,shot,Us,own,final,0.88,0.5,,,9,Test Player,false,,2026-10-01T10:04:00Z,0.200,300000,goal,false\n"
    "First half,06:00,7,pass,Them,opposition,middle,0.5,0.5,,,,,false,,2026-10-01T10:05:00Z,,360000,,\n"
    "Second half,01:00,46,shot,Them,opposition,final,0.95,0.5,,,,,false,,2026-10-01T11:00:00Z,0.700,2800000,saved,true\n"
    "Second half,02:00,47,corner,Us,own,final,0.99,0.98,,,,,false,,2026-10-01T11:01:00Z,,,,\n"
)
