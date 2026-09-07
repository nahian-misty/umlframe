public class User {
    public static final int MAX_LOGIN_ATTEMPTS = 5;
    private String email;
    protected String token;
    private String secret;

    public User(String email) {
        this.email = email;
        this.token = "";
        this.secret = "shh";
    }

    public static String normalizeEmail(String email) {
        return email.toLowerCase();
    }

    public boolean login(String password) {
        return true;
    }

    public boolean equals(Object other) {
        return false;
    }
}
