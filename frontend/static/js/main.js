(() => {
    const el = (selector) => document.querySelector(selector)

    const loadData = () => fetch('/proxy/status')
        .then(r => r.json())
        .then(r => {
            el('#status-on').style.display = r.api_connectivity ? 'block' : 'none'
            el('#status-off').style.display = r.api_connectivity ? 'none' : 'block'
            el('#run-date').innerText = r.run_date

            el('#error').style.display = r.error_msg ? 'block' : 'none'
            el('#error-title').innerText = r.error_title
            el('#error-msg').innerText = r.error_msg

            el('#cache-size').innerText = r.cache_size_mb
            el('#credit').innerText = r.credit

            el('#license-container').style.display = r.license_type ? 'block' : 'none'
            el('#license-type').innerText = r.license_type
            el('#license-active').innerText = r.active ? 'Active' : 'Not Active'
            el('#license-exp').innerText = r.license_expiration

            let lsEl = el('#license-status')
            lsEl.classList.add(r.active ? 'on' : 'off')
            lsEl.classList.remove(r.active ? 'off' : 'on')

            el('#statistic').style.display = r.statistic && Object.keys(r.statistic).length ? 'block' : 'none'
            if (r.statistic) {
                el('#statistic-body').innerHTML = Object.keys(r.statistic)
                    .map(stat => `<tr>
                        <td>${stat}</td>
                        <td>${r.statistic[stat]}</td>
                    </tr>`).join('')
            }

            el("#year").innerText = new Date().getFullYear().toString()
        })

    document.addEventListener('DOMContentLoaded', () => {
        loadData()
        setInterval(loadData, 5000)
    })
})()