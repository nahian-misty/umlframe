public class Animal {
    private String name;

    public Animal(String name) {
        this.name = name;
    }

    public String speak() {
        return "";
    }
}

public class Dog extends Animal implements UnknownMixin {
    public String bark() {
        return "Woof";
    }
}
