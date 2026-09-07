class Engine {
    constructor(horsepower) {
        this.horsepower = horsepower;
    }
}

class Car {
    constructor(owner) {
        this.engine = new Engine(300);
        this.owner = owner;
    }
}
