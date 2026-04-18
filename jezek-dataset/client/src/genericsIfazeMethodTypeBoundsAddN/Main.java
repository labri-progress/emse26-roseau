package genericsIfazeMethodTypeBoundsAddN;

import testing_lib.genericsIfazeMethodTypeBoundsAddN.GenericsIfazeMethodTypeBoundsAddN;

public class Main implements GenericsIfazeMethodTypeBoundsAddN {

	public static void main(String[] args) {
		Main constr = new Main();
		constr.<Integer>method1();
	}

	@Override
	public <T> void method1() {
		
	}

}
