# Architecture

Auth Site is the central identity, profile, registration-code, and site-directory app for the local site family.

The default ingress base path is `/auth`, but every backend URL, frontend route, cookie path, OAuth issuer URL, redirect URL, and avatar URL must derive from configuration.

See:

- [Base Path And Deployment](./base-path-and-deployment.md)
