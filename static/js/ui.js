// Functions related to UI/UX shared across pages

// Search
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('eventSearch');
    const searchMatches = document.getElementById('searchMatches');
    const searchResult = document.getElementById('searchResult');
    let allEvents = [];

    // Fetch all events when page loads
    fetch('/event_list')
        .then(response => response.json())
        .then(events => {
            allEvents = events;
            console.log(allEvents);
        })
        .catch(error => console.error('Error fetching events:', error));

    function showMatches(matches) {
        if (matches.length === 0) {
            searchMatches.style.display = 'none';
            return;
        }

        searchMatches.innerHTML = matches
            .map(event => `
                <div class="p-2 border-bottom cursor-pointer hover-bg-light" 
                     role="button"
                     data-event-id="${event.id}">
                    ${event.title}
                </div>
            `)
            .join('');
        
        searchMatches.style.display = 'block';
    }

    async function fetchAndDisplayEvent(eventId) {
        try {
            const response = await fetch(`/event/${eventId}`);
            const html = await response.text();
            searchResult.innerHTML = html;
            searchMatches.style.display = 'none';
            searchInput.value = allEvents.find(e => e.id === eventId)?.title || '';
        } catch (error) {
            console.error('Error fetching event:', error);
        }
    }

    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase().trim();
        
        if (searchTerm.length < 2) {
            searchMatches.style.display = 'none';
            return;
        }

        const matches = allEvents
            .filter(event => event.title.toLowerCase().includes(searchTerm))
            .slice(0, 5); // Show top 5 matches

        showMatches(matches);
    });

    // Handle clicking on a match
    searchMatches.addEventListener('click', (e) => {
        const matchEl = e.target.closest('[data-event-id]');
        if (matchEl) {
            const eventId = matchEl.dataset.eventId;
            fetchAndDisplayEvent(eventId);
        }
    });

    // Close matches when clicking outside
    document.addEventListener('click', (e) => {
        if (!searchMatches.contains(e.target) && e.target !== searchInput) {
            searchMatches.style.display = 'none';
        }
    });
});

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