package inheritanceIfazeMethodMovedToSuperInterface;

import testing_lib.inheritanceIfazeMethodMovedToSuperInterface.InheritanceIfazeMethodMovedToSuperInterface;
import testing_lib.inheritanceIfazeMethodMovedToSuperInterface.Interface1;

public class Main implements InheritanceIfazeMethodMovedToSuperInterface {

	@Override
	public void method1() {
		
	}

	public static void main(String[] args) {
		InheritanceIfazeMethodMovedToSuperInterface ifaze = new Main();
		ifaze.method1();

		// Even though InheritanceIfazeMethodMovedToSuperInterface isn't breaking, Interface1 is also API
		Interface1 i = new Interface1() {};
	}
	
}
