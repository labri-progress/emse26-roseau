package genericsClazzMethodTypeDeleteSecond;

import testing_lib.genericsClazzMethodTypeDeleteSecond.GenericsClazzMethodTypeDeleteSecond;

public class Main extends GenericsClazzMethodTypeDeleteSecond {

	public static void main(String[] args) {
		GenericsClazzMethodTypeDeleteSecond constr = new GenericsClazzMethodTypeDeleteSecond();
		constr.<Integer, String>method1();
	}

	@Override
	public <T, K> void method1() {

	}
}
