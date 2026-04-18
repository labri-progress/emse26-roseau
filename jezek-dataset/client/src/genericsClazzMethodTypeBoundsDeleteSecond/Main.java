package genericsClazzMethodTypeBoundsDeleteSecond;

import testing_lib.genericsClazzMethodTypeBoundsDeleteSecond.GenericsClazzMethodTypeBoundsDeleteSecond;

public class Main extends GenericsClazzMethodTypeBoundsDeleteSecond {

	public static void main(String[] args) {
		GenericsClazzMethodTypeBoundsDeleteSecond constr = new GenericsClazzMethodTypeBoundsDeleteSecond();
		constr.<Integer>method1();
	}

	@Override
	public <T extends Number & Comparable<T>> void method1() {

	}
}
