# Calibot

A poorly written discord bot with World of Warcraft related functionality

## Commands
### World of Warcraft
 - !affixes -> Shows current mythic+ affixes as shown on wowhead.com
 - !wowtoken -> Shows current wow token gold price as determined by wowtoken.info
 - !armory character realm -> Shows item level, raid progressions, aotc status
 - !logs character realm -> Shows a basic log summary from warcraftlogs.com
 - !wp character realm -> Shows mythic+ dungeon completion rates from wowprogress.com
 - !gear character realm -> Shows equipped character gear and item levels and has a basic enchant/gem check
 - !setmain character realm -> If set will allow commands that require character
 and realm to use this if nothing else is provided
 - !allstars "guild name" "realm" - > Combined realm ranks and character performance data from warcraftlogs.com, must use double quotes if guild or realm contain spaces
 - !guildperf "guild name" "realm" -> Character performance data from warcraftlogs.com for entire raiding guild roster, must use double quotes if guild or realm contain spaces
 - !defaultguild "guild name" "realm" -> Sets guild and realm for !allstars and !guildperf commands for that discord server

 ### Color
  - !colorme class -> Changes your discord color to that World of Warcraft class, can also use a 6 digit hexadecimal number in place of class
  - !removecolor -> Removes your color
 
 ### Misc
   - !announce -> Joins/Leaves/Moves to your voice channel as appropriate and will announce who enters and leaves
   - !set phonetic "text to say" @User -> Overrides name and nickname for the announce command

 ### Permission
  - !toggle commandtype -> Enables/Disables certain commands; only used for color right now
  - !allow commandtype role -> Allows role to use that command type (currently only used for !set) ex. !allow set officers
  - !deny cmmandtype role -> Removes that role from those allowed to use that command type
  