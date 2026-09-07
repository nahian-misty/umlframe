class User {
    constructor(email) {
        this.email = email;
        this._token = "";
    }

    login(password) {
        return true;
    }

    static normalizeEmail(email) {
        return email.toLowerCase();
    }
}
