from auto_logo import TeamSpec, batch_generate

teams = [
    TeamSpec("Buffalo", "Bisons", primary="#0a3161", secondary="#c8102e", abbrev="BUF", template="shield"),
    TeamSpec("Carolina", "Sharks", template="circle"),   # colors auto-picked from mascot family
    TeamSpec("Las Vegas", "Dragons", template="cap", secondary="#f59e0b"),
]
batch_generate(teams, out_dir="logos_demo", size=1024)
