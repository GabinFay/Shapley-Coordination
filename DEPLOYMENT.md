# Deploying NFT Bundle Marketplace on Fly.io

This guide will help you deploy the NFT Bundle Marketplace application on Fly.io.

## Prerequisites

1. Install the Fly CLI: https://fly.io/docs/hands-on/install-flyctl/
2. Sign up for a Fly.io account: https://fly.io/docs/hands-on/sign-up/
3. Log in to Fly.io: `flyctl auth login`

## Deployment Steps

### 1. Initialize the Fly.io App (First-time only)

If you haven't already created the app on Fly.io:

```bash
fly launch
```

This will detect your Dockerfile and create a fly.toml file. You can accept the defaults or customize as needed.

### 2. Set Environment Secrets

Set your environment variables as secrets:

```bash
fly secrets set INFURA_KEY=your_infura_key_here
fly secrets set MARKETPLACE_ADDRESS=0xfc1e512D6783E17C5E8B48Ca7a906A0C13e04224
fly secrets set MOCK_NFT_ADDRESS=0xf1B1ABA247B9953eb36dED56e774c9F3054513D4
fly secrets set USE_LOCAL=false
```

Add any other secrets your application needs.

### 3. Deploy the Application

Deploy your application:

```bash
fly deploy
```

### 4. Open the Application

Once deployed, open your application:

```bash
fly open
```

## Monitoring and Logs

View application logs:

```bash
fly logs
```

Monitor application status:

```bash
fly status
```

## Scaling

To scale your application:

```bash
fly scale count 2  # Scale to 2 instances
```

## Troubleshooting

If you encounter issues:

1. Check the logs: `fly logs`
2. SSH into the VM: `fly ssh console`
3. Restart the application: `fly apps restart`

## Additional Resources

- [Fly.io Documentation](https://fly.io/docs/)
- [Streamlit Deployment Guide](https://docs.streamlit.io/knowledge-base/deploy/) 