# plately_ai/pos_integrations/toast_api.py

import requests
import os
import time

class ToastAPI:
    def __init__(self, api_key=None, restaurant_guid=None, client_id=None, client_secret=None):
        self.api_key = api_key or os.environ.get('TOAST_API_KEY')
        self.restaurant_guid = restaurant_guid or os.environ.get('TOAST_RESTAURANT_GUID')
        self.base_url = "https://ws.toasttab.com"

        # For OAuth 2.0 (newer Toast APIs might require this for some endpoints)
        self.client_id = client_id or os.environ.get('TOAST_CLIENT_ID')
        self.client_secret = client_secret or os.environ.get('TOAST_CLIENT_SECRET')
        self.access_token = None
        self.token_expires_at = None

        if not self.api_key and (not self.client_id or not self.client_secret):
            raise ValueError("Toast API key or (Client ID and Client Secret) is required. Set it via constructor or environment variables.")
        if not self.restaurant_guid:
             raise ValueError("Toast restaurant GUID is required. Set it via constructor or TOAST_RESTAURANT_GUID env variable.")

        self.headers = {
            "Toast-Restaurant-External-ID": self.restaurant_guid,
            "Accept": "application/json"
        }
        if self.api_key: # Legacy authentication
             self.headers["Authorization"] = f"Bearer {self.api_key}"


    def _get_access_token(self):
        """Fetches a new OAuth access token if needed."""
        if self.access_token and self.token_expires_at and time.time() < self.token_expires_at:
            return self.access_token

        if not self.client_id or not self.client_secret:
            # If using legacy API key, this method is not applicable or means misconfiguration.
            if self.api_key:
                return None # Or handle as an error/warning if OAuth is expected
            raise ValueError("Toast Client ID and Client Secret are required for OAuth.")

        token_url = "https://ws.toasttab.com/usermgmt/v1/oauth/token"
        payload = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "grantType": "client_credentials",
            "userAccessType": "TOAST_MACHINE_CLIENT" # Or other appropriate types
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = requests.post(token_url, data=payload, headers=headers)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data["access_token"]
            # Defaulting to 1 hour (3600 seconds) expiry, adjust if 'expires_in' is available
            self.token_expires_at = time.time() + token_data.get("expires_in", 3600) - 60 # 60s buffer
            return self.access_token
        except requests.exceptions.RequestException as e:
            print(f"Error obtaining Toast access token: {e}")
            if response is not None:
                print(f"Response content: {response.text}")
            self.access_token = None
            self.token_expires_at = None
            return None

    def _make_request(self, method, endpoint, params=None, json_data=None, use_oauth=False):
        """Makes a request to the Toast API, handling authentication."""
        url = f"{self.base_url}{endpoint}"
        current_headers = self.headers.copy()

        if use_oauth:
            token = self._get_access_token()
            if not token:
                return None # Failed to get token
            current_headers["Authorization"] = f"Bearer {token}"
            # Remove legacy key if OAuth is used
            current_headers.pop("Toast-Restaurant-External-ID", None) # Some OAuth endpoints might not need this
            current_headers.pop("Toast-Api-Key", None) # Or however legacy key is passed
        elif "Authorization" not in current_headers and self.api_key: # Ensure legacy auth header is set if not using OAuth
             current_headers["Authorization"] = f"Bearer {self.api_key}"


        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=current_headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=current_headers, json=json_data, params=params)
            else:
                print(f"Unsupported HTTP method: {method}")
                return None

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error making {method} request to {url}: {e}")
            if e.response is not None:
                print(f"Response status code: {e.response.status_code}")
                print(f"Response content: {e.response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error making {method} request to {url}: {e}")
        return None

    def get_sales_data(self, start_date, end_date, page_size=500):
        """
        Fetches sales data (orders) from the Toast API (Orders API).
        Requires OAuth 2.0.
        :param start_date: YYYY-MM-DD format
        :param end_date: YYYY-MM-DD format
        :param page_size: Number of records per page
        :return: A list of orders or None if an error occurs.
        """
        if not self.client_id or not self.client_secret:
            print("OAuth (Client ID/Secret) is required for get_sales_data. This endpoint does not support legacy API key.")
            return None

        endpoint = "/orders/v2/ordersBulk"
        all_orders = []
        page = 1

        while True:
            params = {
                "startDate": start_date,
                "endDate": end_date,
                "pageSize": page_size,
                "page": page
            }

            # This endpoint typically requires specific Toast headers for OAuth
            # The _make_request method needs to be flexible enough or this needs custom handling
            # Forcing OAuth for this one:
            token = self._get_access_token()
            if not token:
                return None

            current_headers = {
                "Authorization": f"Bearer {token}",
                "Toast-Restaurant-External-ID": self.restaurant_guid, # Still often needed
                "Accept": "application/json"
            }

            try:
                response = requests.get(f"{self.base_url}{endpoint}", headers=current_headers, params=params)
                response.raise_for_status()
                data = response.json()

                if not data: # No more data or empty response
                    break

                all_orders.extend(data)

                # Toast Orders API v2 ordersBulk is not paginated with a cursor like others.
                # It returns an array of orders. If the array is smaller than pageSize, or empty, it's the last page.
                if len(data) < page_size:
                    break
                page += 1

            except requests.exceptions.RequestException as e:
                print(f"Error fetching sales data from Toast: {e}")
                if response is not None:
                    print(f"Response content: {response.text}")
                return None # Or break, depending on desired error handling for pagination

        return all_orders


    def get_menu_items(self):
        """
        Fetches menus and their items from the Toast API (Menus API).
        Can use legacy API key or OAuth. We'll try OAuth first if configured.
        """
        endpoint = "/config/v2/menus" # This gets menu groups, items, option groups etc.

        use_oauth_flag = bool(self.client_id and self.client_secret)

        data = self._make_request("GET", endpoint, use_oauth=use_oauth_flag)

        if data:
            # The structure of /config/v2/menus is a list of full menu objects.
            # Each menu object contains groups, which contain items, etc.
            return data # Returns the full menu structure
        else:
            print("Failed to fetch menu items from Toast.")
            return None

if __name__ == '__main__':
    print("Attempting to initialize ToastAPI...")
    try:
        # Ensure TOAST_API_KEY (or TOAST_CLIENT_ID & TOAST_CLIENT_SECRET) and TOAST_RESTAURANT_GUID are set as env vars
        toast_client = ToastAPI()
        print("ToastAPI initialized.")

        print("\nFetching menu items...")
        menu_data = toast_client.get_menu_items()
        if menu_data:
            print(f"Successfully fetched {len(menu_data)} menu structures from Toast.")
            # Example: print names of all menus
            # for menu in menu_data:
            #     print(f"- Menu Name: {menu.get('name')}")
            #     for group in menu.get('menuGroups', []):
            #         print(f"  - Group: {group.get('name')}")
            #         for item in group.get('menuItems', []):
            #             print(f"    - Item: {item.get('name')}")
        else:
            print("Failed to fetch menu items or no menus found.")

        # Sales data fetching requires OAuth (client_id, client_secret) and a date range
        if toast_client.client_id and toast_client.client_secret:
            print("\nFetching sales data (orders)... (Requires OAuth and date range)")
            from datetime import datetime, timedelta
            # Example: Fetch orders from yesterday
            end_dt_str = (datetime.utcnow() - timedelta(days=0)).strftime('%Y-%m-%d')
            start_dt_str = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')

            print(f"Fetching sales from {start_dt_str} to {end_dt_str}")
            sales = toast_client.get_sales_data(start_date=start_dt_str, end_date=end_dt_str)
            if sales is not None: # Check for None explicitly as an empty list is a valid (no sales) response
                print(f"Successfully fetched {len(sales)} orders/transactions.")
                # for order in sales[:2]: # Print details of first 2 orders
                #     print(order)
            else:
                print("Failed to fetch sales data or no sales found in the period.")
        else:
            print("\nSkipping sales data fetching: Toast Client ID and/or Client Secret not configured for OAuth.")

    except ValueError as ve:
        print(f"Configuration error: {ve}")
    except Exception as ex:
        print(f"An unexpected error occurred: {ex}")
