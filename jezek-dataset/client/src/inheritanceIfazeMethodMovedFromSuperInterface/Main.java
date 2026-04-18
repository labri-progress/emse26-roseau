package inheritanceIfazeMethodMovedFromSuperInterface;

import testing_lib.inheritanceIfazeMethodMovedFromSuperInterface.InheritanceIfazeMethodMovedFromSuperInterface;
import testing_lib.inheritanceIfazeMethodMovedFromSuperInterface.Interface1;

public class Main implements InheritanceIfazeMethodMovedFromSuperInterface {

	@Override
	public void method1() {
		
	}

	public static void main(String[] args) {
		InheritanceIfazeMethodMovedFromSuperInterface ifaze = new Main();
		ifaze.method1();
		// Even though , InheritanceIfazeMethodMovedFromSuperInterface isn't breaking Interface1 is also API
		Interface1 i = new Main();
		i.method1();
	}
	
}
