# Weather & Privacy

PIXEL V11 has two weather location modes:

- **Automatic:** Uses ip-api.com to estimate coarse city/country and latitude/longitude from the current network IP. PIXEL does not store the returned IP address.
- **Manual:** Uses the city entered in Settings and does not contact the IP geolocation endpoint.

Weather data is fetched from wttr.in.

If a VPN or proxy is active, automatic location may reflect the VPN/proxy exit location. Turn off **Auto Location** and enter a city manually in that case.
