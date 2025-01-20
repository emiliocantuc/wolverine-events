// Functions related to UI/UX shared across pages

function toggleVoteButtons(event_id, dir, hx_div) {
    // Handles button presses in card feeds (change UI and send PUT)
   
    let upButtons =  document.querySelectorAll('[name="'+ event_id +'_up"]');
    let downButtons = document.querySelectorAll('[name="'+ event_id +'_down"]');
    let counters = document.querySelectorAll('[name="'+ event_id +'_count"]');
    let counterInt = parseInt(counters[0].textContent, 10);
    let upSelected = upButtons[0].classList.contains('text-warning');
    let downSelected = downButtons[0].classList.contains('text-warning');
    let url = '';

    console.log(upButtons)
    // If we clicked upvote and up was not selected
    if (dir == 'up' && !upSelected) {
        for(let i = 0; i < counters.length; i++){
            console.log(i, upButtons[i].classList)
            upButtons[i].classList.add('text-warning');
            downButtons[i].classList.remove('text-warning');
            counters[i].textContent = counterInt + (downSelected ? 2: 1);
        }
        url = `/vote?eventId=${event_id}&type=U&factor=1`;
    }
    // We clicked up but it was already selected
    else if (dir == 'up' && upSelected) {
        for(let i = 0; i < counters.length; i++){
            upButtons[i].classList.remove('text-warning');
            counters[i].textContent = counterInt - 1;
        }
        url = `/vote?eventId=${event_id}&type=N&factor=-1`;
    }
    // We clicked down and it was not selected
    else if (dir == 'down' && !downSelected) {
        for(let i = 0; i < counters.length; i++){
            upButtons[i].classList.remove('text-warning');
            downButtons[i].classList.add('text-warning');
            counters[i].textContent = counterInt - (upSelected ? 2: 1);
        }
        url = `/vote?eventId=${event_id}&type=D&factor=-1`;
    }
    // Clicked down and it was already selected
    else if (dir == 'down' && downSelected) {
        for(let i = 0; i < counters.length; i++){
            downButtons[i].classList.remove('text-warning');
            counters[i].textContent = counterInt + 1;
        }
        url = `/vote?eventId=${event_id}&type=N&factor=1`;
    }
    fetch(url, { method: 'PUT' });
}