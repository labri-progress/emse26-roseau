package genericsIfazeMethodTypeDeleteN;

import testing_lib.genericsIfazeMethodTypeDeleteN.GenericsIfazeMethodTypeDeleteN;

public class Main implements GenericsIfazeMethodTypeDeleteN {

	public static void main(String[] args) {
		Main constr = new Main();
		constr.<Integer>method1();
	}

	@Override
	public <T> void method1() {
		
	}
		
}
