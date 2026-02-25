# Jinko API Helpers

Python helpers function to ease use of Jinko's API

Jinko is an innovative SaaS and CaaS platform focused on trial simulation and design optimization. The Jinko API offers programmatic access to a wide range of functionalities, facilitating integration with various tools and enhancing collaboration.

## Usage

```sh
pip install jinko-sdk

# Or

poetry add jinko-sdk

```

Install optional modules only when needed:

```sh
# Full jinko_helpers feature set (trial/dataframe helpers)
pip install "jinko-sdk[jinko_helpers]"

# jinko_stats
pip install "jinko-sdk[jinko_stats]"

# crabbit
pip install "jinko-sdk[crabbit]"

# jinko_nn
pip install "jinko-sdk[jinko_nn]"

# everything
pip install "jinko-sdk[full]"
```

```python
import jinko_helpers as jinko

# Connect to Jinko
jinko.initialize(
    projectId='016140de-1753-4133-8cbf-e67d9a399ec1',
    apiKey='50b5085e-3675-40c9-b65b-2aa8d0af101c'
)

# Check authentication
response = jinko.makeRequest('/app/v1/auth/check')

# Make a few requests
projectItem = jinko.makeRequest(
    '/app/v1/project-item/tr-EUsp-WjjI',
    method='GET',
).json()

```


## Contributing

Check the [dedicated instructions](./CONTRIBUTING.md).

Find out more at [Jinko Doc](https://doc.jinko.ai)
