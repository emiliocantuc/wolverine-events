# wolverine-events

A simple content-based filtering recommender system for University of Michigan events. Write-up [here](https://emiliocantuc.github.io/posts/posts/wolv-events/).

In development. Hosted (sometimes) at [mywolverine.events](https://mywolverine.events/).

## How to run 
1. Create `.env` file with 
```
GOOGLE_CLIENT_ID=[The app's client ID]
SESSION_SECRET=[key used to sign sessions with. For example, generated w/openssl rand -hex 32]
NTFY_CHANNEL=[ntfy.sh topic for maintenance notifications]

```
Note: last line must be empty!

2. Create `email_params.json` file with
```json
{
    "token":[token used in script],
    "url":[appscript url that sends email],
    "subject":"Your recommendations are ready",
    "recipient":"mywolverineevents@umich.edu"
}
```
3. Create `email.txt` with weekly message. For example:
```
Hi,

Your weekly event recommendations are ready at https://mywolverine.events

Best,
Emilio

You received this email because you signed up to the site (https://mywolverine.events) and joined the MCommunity group https://mcommunity.umich.edu/group/Event%20Recommentations. To stop receiving these emails follow the group link and press "Leave Group".
```

4. Install dependencies w/`pip install -r requirements.txt` and run `sudo sh serve.sh`

## TODOs
- Check str rep of sporting events: do co-sponsors how up?
- Skip events user has already rated
- diversify feed (sample using predicted rating?)