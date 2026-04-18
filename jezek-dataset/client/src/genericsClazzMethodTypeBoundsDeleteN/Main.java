package genericsClazzMethodTypeBoundsDeleteN;

import testing_lib.genericsClazzMethodTypeBoundsDeleteN.GenericsClazzMethodTypeBoundsDeleteN;

public class Main extends GenericsClazzMethodTypeBoundsDeleteN {
	
	public static void main(String[] args) {
		GenericsClazzMethodTypeBoundsDeleteN constr = new GenericsClazzMethodTypeBoundsDeleteN();
		constr.<Integer>method1();
	}

	@Override
	public <T extends Number> void method1() {

	}
}
