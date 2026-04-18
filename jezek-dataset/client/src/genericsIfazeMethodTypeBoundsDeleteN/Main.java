package genericsIfazeMethodTypeBoundsDeleteN;

import testing_lib.genericsIfazeMethodTypeBoundsDeleteN.GenericsIfazeMethodTypeBoundsDeleteN;

public class Main implements GenericsIfazeMethodTypeBoundsDeleteN {

	public static void main(String[] args) {
		Main constr = new Main();
		constr.<Integer>method1();
	}

	@Override
	public <T extends Number> void method1() {
		
	}
	
}
