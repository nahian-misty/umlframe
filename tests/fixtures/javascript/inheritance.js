class Animal {
    constructor(name) {
        this.name = name;
    }

    speak() {
        return "";
    }
}

class Dog extends Animal {
    bark() {
        return "Woof";
    }
}
