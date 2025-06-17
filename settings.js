module.exports = {
    credentialSecret: process.env.NODE_RED_CREDENTIAL_SECRET,
    adminAuth: {
        type: "credentials",
        users: [{
            username: "admin",
            password: "$2a$08$zZWtXTja0fB1pzD4sHCMyOCMYz2Z6dNbM6tl8sJogENOMcxWV9DN.",
            permissions: "*"
        }]
    },
    functionGlobalContext: {
        pythonService: "http://python-service:8000"
    }
}