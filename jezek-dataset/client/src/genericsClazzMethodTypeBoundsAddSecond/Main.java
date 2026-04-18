package genericsClazzMethodTypeBoundsAddSecond;

import testing_lib.genericsClazzMethodTypeBoundsAddSecond.GenericsClazzMethodTypeBoundsAddSecond;

public class Main extends GenericsClazzMethodTypeBoundsAddSecond {

	public static void main(String[] args) {
		GenericsClazzMethodTypeBoundsAddSecond constr = new GenericsClazzMethodTypeBoundsAddSecond();
		constr.<Number>method1();
	}

	@Override
	public <T extends Number> void method1() {

	}

}
