public class Engine {
    private int horsepower;

    public Engine(int horsepower) {
        this.horsepower = horsepower;
    }
}

public class Wheel {
    private int size;

    public Wheel(int size) {
        this.size = size;
    }
}

public class Person {
    private String name;

    public Person(String name) {
        this.name = name;
    }
}

public class Car {
    private Engine engine;
    private Person owner;
    private List<Wheel> wheels;

    public Car(Person owner) {
        this.engine = new Engine(300);
        this.owner = owner;
    }

    public void registerOwner(Person owner) {
    }
}
